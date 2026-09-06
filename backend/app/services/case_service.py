from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.repositories import (
    AuditRepository,
    CaseRepository,
    EvidenceRepository,
    IdempotencyConflictError,
    IdempotencyRepository,
    ProviderContextRepository,
    TimelineRepository,
    utc_now,
)
from app.adapters.synthetic_providers import SyntheticBankingProvider
from app.domain.schemas import (
    CaseListResponse,
    CaseResponse,
    CaseStatus,
    CaseSummaryResponse,
    Channel,
    CreateCaseRequest,
    EvidenceListResponse,
    EvidenceMetadataIn,
    EvidenceMetadataOut,
    EvidenceRegistrationResponse,
    TimelineEntryOut,
    TimelineResponse,
)

CREATE_CASE_OPERATION = "create-case"


class CaseNotFoundError(Exception):
    pass


def fingerprint_request(request: BaseModel) -> str:
    payload = request.model_dump(mode="json")
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


class CaseService:
    def __init__(
        self,
        db: Session,
        provider: SyntheticBankingProvider | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self.db = db
        self.provider = provider or SyntheticBankingProvider()
        self.case_repository = CaseRepository(db)
        self.idempotency_repository = IdempotencyRepository(db)
        self.evidence_repository = EvidenceRepository(db)
        self.provider_context_repository = ProviderContextRepository(db)
        self.audit_repository = audit_repository or AuditRepository(db)
        self.timeline_repository = TimelineRepository(db)

    def create_case(
        self,
        request: CreateCaseRequest,
        idempotency_key: str,
        correlation_id: str,
    ) -> tuple[CaseResponse, bool]:
        fingerprint = fingerprint_request(request)
        existing = self.idempotency_repository.get(CREATE_CASE_OPERATION, idempotency_key)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflictError("idempotency key reused for different payload")
            self.idempotency_repository.mark_replayed(existing, utc_now())
            self.db.commit()
            if existing.response_json is None:
                raise RuntimeError("completed idempotency record has no response")
            return CaseResponse.model_validate(existing.response_json), True

        now = utc_now()
        try:
            with self.db.begin_nested():
                case = self.case_repository.add_case(request, correlation_id, now)
                provider_results = self.provider.collect_context(
                    request.customer_ref, request.account_ref, request.transaction_ref
                )
                self.provider_context_repository.add_results(
                    case.case_id, correlation_id, provider_results
                )
                case_audit = self.audit_repository.append_case_created(case, now)
                self.timeline_repository.add_case_created(case, case_audit, now)
                for evidence_input in request.evidence_metadata:
                    evidence = self.evidence_repository.add(
                        case.case_id, evidence_input, correlation_id, now
                    )
                    evidence_audit = self.audit_repository.append_evidence_registered(
                        case, evidence, case.state_version, correlation_id, now
                    )
                    self.timeline_repository.add(
                        case_id=case.case_id,
                        event_type="EVIDENCE_METADATA_REGISTERED",
                        message=f"Evidence metadata registered: {evidence.file_name}.",
                        audit_event=evidence_audit,
                        correlation_id=correlation_id,
                        now=now,
                    )
                self.db.flush()

                detail = self.case_repository.get_detail(case.case_id)
                if detail is None:
                    raise CaseNotFoundError(case.case_id)
                response = self._to_response(detail)
                self.idempotency_repository.add(
                    CREATE_CASE_OPERATION,
                    idempotency_key,
                    fingerprint,
                    case.case_id,
                    jsonable_encoder(response),
                    201,
                    correlation_id,
                    now,
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return response, False

    def get_case(self, case_id: str) -> CaseResponse:
        detail = self.case_repository.get_detail(case_id)
        if detail is None:
            raise CaseNotFoundError(case_id)
        return self._to_response(detail)

    def list_cases(
        self,
        *,
        status: CaseStatus | None = None,
        customer_ref: str | None = None,
        transaction_ref: str | None = None,
        channel: Channel | None = None,
        opened_from: datetime | None = None,
        opened_to: datetime | None = None,
    ) -> CaseListResponse:
        cases = self.case_repository.list_cases(
            status=status.value if status else None,
            customer_ref=customer_ref,
            transaction_ref=transaction_ref,
            channel=channel.value if channel else None,
            opened_from=opened_from,
            opened_to=opened_to,
        )
        items = [CaseSummaryResponse.model_validate(case) for case in cases]
        return CaseListResponse(items=items, total=len(items))

    def register_evidence(
        self,
        *,
        case_id: str,
        request: EvidenceMetadataIn,
        idempotency_key: str,
        expected_version: int,
        correlation_id: str,
    ) -> EvidenceRegistrationResponse:
        operation = f"register-evidence:{case_id}"
        fingerprint = fingerprint_request(request)
        existing = self.idempotency_repository.get(operation, idempotency_key)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflictError("idempotency key reused for different payload")
            self.idempotency_repository.mark_replayed(existing, utc_now())
            self.db.commit()
            if existing.response_json is None:
                raise RuntimeError("completed idempotency record has no response")
            replay = EvidenceRegistrationResponse.model_validate(existing.response_json)
            return replay.model_copy(update={"replayed": True})

        case = self.case_repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)

        now = utc_now()
        try:
            with self.db.begin_nested():
                new_version = self.case_repository.increment_version(case_id, expected_version, now)
                case.state_version = new_version
                case.updated_at = now
                evidence = self.evidence_repository.add(case_id, request, correlation_id, now)
                audit_event = self.audit_repository.append_evidence_registered(
                    case, evidence, new_version, correlation_id, now
                )
                self.timeline_repository.add(
                    case_id=case_id,
                    event_type="EVIDENCE_METADATA_REGISTERED",
                    message=f"Evidence metadata registered: {evidence.file_name}.",
                    audit_event=audit_event,
                    correlation_id=correlation_id,
                    now=now,
                )
                self.db.flush()
                response = EvidenceRegistrationResponse(
                    evidence=EvidenceMetadataOut.model_validate(evidence),
                    state_version=new_version,
                )
                self.idempotency_repository.add(
                    operation,
                    idempotency_key,
                    fingerprint,
                    case_id,
                    jsonable_encoder(response),
                    201,
                    correlation_id,
                    now,
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return response

    def list_evidence(self, case_id: str) -> EvidenceListResponse:
        self._require_case(case_id)
        items = [
            EvidenceMetadataOut.model_validate(item)
            for item in self.evidence_repository.list_for_case(case_id)
        ]
        return EvidenceListResponse(items=items, total=len(items))

    def get_timeline(self, case_id: str) -> TimelineResponse:
        self._require_case(case_id)
        items = [
            TimelineEntryOut.model_validate(item)
            for item in self.timeline_repository.list_for_case(case_id)
        ]
        return TimelineResponse(items=items, total=len(items))

    def case_count(self) -> int:
        return self.case_repository.count()

    def _require_case(self, case_id: str) -> None:
        if self.case_repository.get(case_id) is None:
            raise CaseNotFoundError(case_id)

    def _to_response(self, case: Any) -> CaseResponse:
        case.timeline.sort(
            key=lambda item: (
                item.occurred_at,
                0 if item.event_type == "CASE_CREATED" else 1,
                item.timeline_entry_id,
            )
        )
        case.evidence_metadata.sort(key=lambda item: (item.registered_at, item.evidence_id))
        case.provider_context.sort(key=lambda item: (item.record_type, item.provider_context_id))
        case.audit_events.sort(
            key=lambda item: (
                item.created_at,
                0 if item.event_type == "CASE_CREATED" else 1,
                item.audit_event_id,
            )
        )
        response = CaseResponse.model_validate(case)
        return response.model_copy(
            update={
                "idempotency_replay_count": self.idempotency_repository.replay_count_for_case(
                    case.case_id
                )
            }
        )
