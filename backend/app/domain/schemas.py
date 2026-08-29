from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseStatus(StrEnum):
    draft = "Draft"
    submitted = "Submitted"
    manual_processing = "Manual Processing"
    closed = "Closed"


class DisputeType(StrEnum):
    duplicate_card_transaction = "duplicate_card_transaction"
    failed_upi_transfer = "failed_upi_transfer"
    atm_debit_without_cash = "atm_debit_without_cash"


class Channel(StrEnum):
    web = "web"
    mobile = "mobile"
    analyst = "analyst"
    partner_api = "partner_api"


class EvidenceMetadataIn(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    uploader_ref: str = Field(min_length=1, max_length=80)


class CreateDisputeRequest(BaseModel):
    customer_ref: str = Field(min_length=1, max_length=80)
    account_ref: str | None = Field(default=None, max_length=80)
    transaction_ref: str = Field(min_length=1, max_length=80)
    channel: Channel
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


class EvidenceMetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    uploader_ref: str
    uploaded_at: datetime


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
    event_type: str
    message: str
    audit_event_id: UUID | None
    correlation_id: str
    occurred_at: datetime


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_event_id: UUID
    event_type: str
    actor_type: str
    actor_ref: str
    source: str
    object_ref: str | None
    before_hash: str | None
    after_hash: str | None
    event_metadata: dict[str, object]
    correlation_id: str
    created_at: datetime


class DisputeCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: UUID
    customer_ref: str
    account_ref: str | None
    transaction_ref: str
    channel: Channel
    dispute_type: DisputeType
    description: str
    status: CaseStatus
    correlation_id: str
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime
    timeline: list[TimelineEntryOut] = Field(default_factory=list)
    evidence_metadata: list[EvidenceMetadataOut] = Field(default_factory=list)
    provider_context: list[ProviderContextOut] = Field(default_factory=list)
    audit_events: list[AuditEventOut] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    correlation_id: str | None = None
