from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi.encoders import jsonable_encoder
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
from app.domain.schemas import CreateDisputeRequest, DisputeCaseResponse

CREATE_DISPUTE_OPERATION = "create-dispute"


class CaseNotFoundError(Exception):
    pass


def fingerprint_request(request: CreateDisputeRequest) -> str:
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
        request: CreateDisputeRequest,
        idempotency_key: str,
        correlation_id: str,
    ) -> tuple[DisputeCaseResponse, bool]:
        fingerprint = fingerprint_request(request)
        existing = self.idempotency_repository.get(CREATE_DISPUTE_OPERATION, idempotency_key)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflictError("idempotency key reused for different payload")
            return DisputeCaseResponse.model_validate(existing.response_json), True

        now = utc_now()
        with self.db.begin_nested():
            case = self.case_repository.add_case(request, correlation_id, now)
            provider_results = self.provider.collect_context(
                request.customer_ref, request.account_ref, request.transaction_ref
            )
            self.provider_context_repository.add_results(
                case.case_id, correlation_id, provider_results
            )
            self.evidence_repository.add_from_request(case.case_id, request, now)
            audit_event = self.audit_repository.append_case_created(case, now)
            self.timeline_repository.add_case_created(case, audit_event, now)
            self.db.flush()

            detail = self.case_repository.get_detail(case.case_id)
            if detail is None:
                raise CaseNotFoundError(case.case_id)
            response = self._to_response(detail)
            response_payload = jsonable_encoder(response)
            self.idempotency_repository.add(
                CREATE_DISPUTE_OPERATION,
                idempotency_key,
                fingerprint,
                case.case_id,
                response_payload,
                201,
                correlation_id,
                now,
            )
        self.db.commit()
        return response, False

    def get_case(self, case_id: str) -> DisputeCaseResponse:
        detail = self.case_repository.get_detail(case_id)
        if detail is None:
            raise CaseNotFoundError(case_id)
        return self._to_response(detail)

    def case_count(self) -> int:
        return self.case_repository.count()

    def _to_response(self, case: Any) -> DisputeCaseResponse:
        case.timeline.sort(key=lambda item: item.occurred_at)
        case.audit_events.sort(key=lambda item: item.created_at)
        return DisputeCaseResponse.model_validate(case)
