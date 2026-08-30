from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseStatus(StrEnum):
    draft = "Draft"
    submitted = "Submitted"
    manual_processing = "Manual Processing"
    closed = "Closed"


ALLOWED_CASE_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.draft: frozenset({CaseStatus.submitted}),
    CaseStatus.submitted: frozenset(),
    CaseStatus.manual_processing: frozenset(),
    CaseStatus.closed: frozenset(),
}


def validate_case_transition(current: CaseStatus, target: CaseStatus) -> None:
    if target not in ALLOWED_CASE_TRANSITIONS[current]:
        message = f"Unsupported Phase 002 case transition: {current.value} -> {target.value}"
        raise ValueError(message)


class DisputeType(StrEnum):
    duplicate_card_transaction = "duplicate_card_transaction"
    failed_upi_transfer = "failed_upi_transfer"
    atm_debit_without_cash = "atm_debit_without_cash"


class Channel(StrEnum):
    web = "web"
    mobile = "mobile"
    analyst = "analyst"
    partner_api = "partner_api"


class EvidenceType(StrEnum):
    receipt = "receipt"
    transaction_record = "transaction_record"
    customer_statement = "customer_statement"
    other = "other"


class EvidenceStatus(StrEnum):
    registered = "registered"


class EvidenceMetadataIn(BaseModel):
    evidence_type: EvidenceType = EvidenceType.other
    file_name: str = Field(min_length=1, max_length=255)
    object_ref: str | None = Field(default=None, max_length=500)
    content_type: str = Field(pattern=r"^[a-z0-9.+-]+/[a-z0-9.+-]+$", max_length=120)
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    source: str = Field(default="customer_upload", min_length=1, max_length=80)
    uploader_ref: str = Field(min_length=1, max_length=80)

    @field_validator("checksum_sha256")
    @classmethod
    def normalize_checksum(cls, value: str) -> str:
        return value.lower()


class CreateCaseRequest(BaseModel):
    customer_ref: str = Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=80)
    account_ref: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=80
    )
    transaction_ref: str = Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=80)
    channel: Channel
    channel_metadata: dict[str, object] = Field(default_factory=dict)
    description: str = Field(min_length=10, max_length=4000)
    dispute_type: DisputeType = DisputeType.duplicate_card_transaction
    submitted_at: datetime | None = None
    evidence_metadata: list[EvidenceMetadataIn] = Field(default_factory=list)

    @field_validator("submitted_at")
    @classmethod
    def normalize_submitted_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("dispute_type")
    @classmethod
    def require_phase_002_dispute_type(cls, value: DisputeType) -> DisputeType:
        if value is not DisputeType.duplicate_card_transaction:
            raise ValueError("Phase 002 supports duplicate_card_transaction only")
        return value


CreateDisputeRequest = CreateCaseRequest


class EvidenceMetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: UUID
    case_id: UUID
    evidence_type: EvidenceType
    file_name: str
    object_ref: str | None
    content_type: str
    size_bytes: int
    checksum_sha256: str
    source: str
    status: EvidenceStatus
    uploader_ref: str
    correlation_id: str
    registered_at: datetime


class ProviderContextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider_context_id: UUID
    provider_name: str
    source_record_ref: str
    record_type: str
    payload_json: dict[str, object]
    response_hash: str
    response_version: str
    correlation_id: str
    retrieved_at: datetime


class TimelineEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeline_entry_id: UUID
    case_id: UUID
    event_type: str
    message: str
    actor: str
    source: str
    audit_event_id: UUID | None
    correlation_id: str
    occurred_at: datetime


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_event_id: UUID
    case_id: UUID
    event_type: str
    actor_type: str
    actor_ref: str
    source: str
    object_ref: str | None
    before_hash: str | None
    after_hash: str | None
    state_version: int
    event_metadata: dict[str, object]
    correlation_id: str
    created_at: datetime


class CaseSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: UUID
    customer_ref: str
    account_ref: str | None
    transaction_ref: str
    channel: Channel
    dispute_type: DisputeType
    status: CaseStatus
    correlation_id: str
    state_version: int
    opened_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class CaseResponse(CaseSummaryResponse):
    channel_metadata: dict[str, object]
    description: str
    submitted_at: datetime
    created_at: datetime
    timeline: list[TimelineEntryOut] = Field(default_factory=list)
    evidence_metadata: list[EvidenceMetadataOut] = Field(default_factory=list)
    provider_context: list[ProviderContextOut] = Field(default_factory=list)
    audit_events: list[AuditEventOut] = Field(default_factory=list)
    idempotency_replay_count: int = 0


DisputeCaseResponse = CaseResponse


class CaseListResponse(BaseModel):
    items: list[CaseSummaryResponse]
    total: int


class EvidenceRegistrationResponse(BaseModel):
    evidence: EvidenceMetadataOut
    state_version: int
    replayed: bool = False


class EvidenceListResponse(BaseModel):
    items: list[EvidenceMetadataOut]
    total: int


class TimelineResponse(BaseModel):
    items: list[TimelineEntryOut]
    total: int


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    correlation_id: str
    details: list[dict[str, object]] = Field(default_factory=list)


def parse_if_match(value: str) -> int:
    normalized = value.strip()
    match = re.fullmatch(r'(?:W/)?"?(\d+)"?', normalized)
    if match is None:
        raise ValueError("If-Match must contain a positive integer case version")
    version = int(match.group(1))
    if version < 1:
        raise ValueError("If-Match must contain a positive integer case version")
    return version
