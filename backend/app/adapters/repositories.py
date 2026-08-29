from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.adapters.models import (
    AuditEventModel,
    CaseModel,
    EvidenceMetadataModel,
    IdempotencyRecordModel,
    ProviderContextModel,
    TimelineEntryModel,
)
from app.adapters.synthetic_providers import ProviderResult
from app.domain.schemas import CaseStatus, CreateDisputeRequest


class IdempotencyConflictError(Exception):
    pass


class AuditWriteError(Exception):
    pass


class IdempotencyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, operation: str, key: str) -> IdempotencyRecordModel | None:
        return self.db.scalar(
            select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.operation == operation,
                IdempotencyRecordModel.idempotency_key == key,
            )
        )

    def add(
        self,
        operation: str,
        key: str,
        request_fingerprint: str,
        case_id: str,
        response_json: dict[str, object],
        status_code: int,
        correlation_id: str,
        created_at: datetime,
    ) -> None:
        self.db.add(
            IdempotencyRecordModel(
                operation=operation,
                idempotency_key=key,
                request_fingerprint=request_fingerprint,
                case_id=case_id,
                response_json=response_json,
                status_code=status_code,
                correlation_id=correlation_id,
                created_at=created_at,
            )
        )


class CaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_case(
        self,
        request: CreateDisputeRequest,
        correlation_id: str,
        now: datetime,
    ) -> CaseModel:
        case = CaseModel(
            case_id=str(uuid4()),
            customer_ref=request.customer_ref,
            account_ref=request.account_ref,
            transaction_ref=request.transaction_ref,
            channel=request.channel.value,
            dispute_type=request.dispute_type.value,
            description=request.description,
            status=CaseStatus.submitted.value,
            correlation_id=correlation_id,
            submitted_at=request.submitted_at or now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(case)
        return case

    def get_detail(self, case_id: str) -> CaseModel | None:
        stmt = (
            select(CaseModel)
            .where(CaseModel.case_id == case_id)
            .options(
                selectinload(CaseModel.timeline),
                selectinload(CaseModel.evidence_metadata),
                selectinload(CaseModel.provider_context),
                selectinload(CaseModel.audit_events),
            )
        )
        return self.db.scalar(stmt)

    def count(self) -> int:
        return len(self.db.scalars(select(CaseModel)).all())


class EvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_from_request(
        self,
        case_id: str,
        request: CreateDisputeRequest,
        now: datetime,
    ) -> None:
        for evidence in request.evidence_metadata:
            self.db.add(
                EvidenceMetadataModel(
                    evidence_id=str(uuid4()),
                    case_id=case_id,
                    file_name=evidence.file_name,
                    content_type=evidence.content_type,
                    size_bytes=evidence.size_bytes,
                    checksum_sha256=evidence.checksum_sha256,
                    uploader_ref=evidence.uploader_ref,
                    uploaded_at=now,
                )
            )


class ProviderContextRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_results(self, case_id: str, correlation_id: str, results: list[ProviderResult]) -> None:
        for result in results:
            self.db.add(
                ProviderContextModel(
                    provider_context_id=str(uuid4()),
                    case_id=case_id,
                    provider_name=result.provider_name,
                    source_record_ref=result.source_record_ref,
                    record_type=result.record_type,
                    payload_json=result.payload,
                    response_hash=result.response_hash,
                    response_version=result.response_version,
                    correlation_id=correlation_id,
                    retrieved_at=result.retrieved_at,
                )
            )


class AuditRepository:
    def __init__(self, db: Session, fail_writes: bool = False) -> None:
        self.db = db
        self.fail_writes = fail_writes

    def append_case_created(self, case: CaseModel, now: datetime) -> AuditEventModel:
        if self.fail_writes:
            raise AuditWriteError("simulated audit write failure")
        event = AuditEventModel(
            audit_event_id=str(uuid4()),
            case_id=case.case_id,
            event_type="CASE_CREATED",
            actor_type="SERVICE",
            actor_ref="case-service",
            source="foundation-api",
            object_ref=case.case_id,
            before_hash=None,
            after_hash=None,
            event_metadata={
                "status": case.status,
                "dispute_type": case.dispute_type,
                "transaction_ref": case.transaction_ref,
            },
            correlation_id=case.correlation_id,
            created_at=now,
        )
        self.db.add(event)
        return event


class TimelineRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_case_created(
        self,
        case: CaseModel,
        audit_event: AuditEventModel,
        now: datetime,
    ) -> None:
        self.db.add(
            TimelineEntryModel(
                timeline_entry_id=str(uuid4()),
                case_id=case.case_id,
                event_type="CASE_CREATED",
                message="Synthetic dispute case created.",
                audit_event_id=audit_event.audit_event_id,
                correlation_id=case.correlation_id,
                occurred_at=now,
            )
        )


def utc_now() -> datetime:
    return datetime.now(UTC)
