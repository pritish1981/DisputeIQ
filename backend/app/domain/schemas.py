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


class PolicyStatus(StrEnum):
    approved = "approved"
    active = "active"
    draft = "draft"
    inactive = "inactive"
    superseded = "superseded"


class PolicySourceType(StrEnum):
    approved_policy = "approved_policy"
    historical_case = "historical_case"
    customer_evidence = "customer_evidence"
    analyst_note = "analyst_note"
    non_policy_example = "non_policy_example"


class PolicySectionIn(BaseModel):
    section: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=10000)


class PolicyDocumentIn(BaseModel):
    document_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$", min_length=1, max_length=120)
    version: str = Field(pattern=r"^[A-Za-z0-9_.-]+$", min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=255)
    status: PolicyStatus
    approval_ref: str = Field(min_length=1, max_length=120)
    source_identity: str = Field(min_length=1, max_length=160)
    source_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    effective_from: datetime
    effective_to: datetime | None = None
    product: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=80)
    jurisdiction: str = Field(min_length=1, max_length=80)
    source_type: PolicySourceType = PolicySourceType.approved_policy
    sections: list[PolicySectionIn] = Field(min_length=1)

    @field_validator("source_checksum_sha256")
    @classmethod
    def normalize_source_checksum(cls, value: str) -> str:
        return value.lower()

    @field_validator("effective_from", "effective_to")
    @classmethod
    def normalize_policy_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class PolicyIngestionRequest(BaseModel):
    documents: list[PolicyDocumentIn] = Field(min_length=1)
    actor_ref: str = Field(default="policy-admin", min_length=1, max_length=100)
    parser_version: str = Field(default="parser-v1", min_length=1, max_length=40)
    chunking_config_hash: str = Field(default="chunking-v1", min_length=1, max_length=64)
    embedding_model: str = Field(
        default="deterministic-test-embedding-v1", min_length=1, max_length=80
    )
    embedding_config_hash: str = Field(default="embedding-config-v1", min_length=1, max_length=64)
    retrieval_index_config_hash: str = Field(
        default="retrieval-index-v1", min_length=1, max_length=64
    )


class PolicyChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: str
    version: str
    section: str
    status: PolicyStatus
    effective_from: datetime
    effective_to: datetime | None
    product: str
    channel: str
    jurisdiction: str
    content: str
    source_checksum_sha256: str
    chunk_hash: str
    parser_version: str
    chunking_config_hash: str
    embedding_model: str
    embedding_config_hash: str
    vector_index_ready: bool
    lexical_index_ready: bool
    ingestion_run_id: UUID
    correlation_id: str


class PolicyDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    version: str
    title: str
    status: PolicyStatus
    approval_ref: str
    source_identity: str
    source_checksum_sha256: str
    effective_from: datetime
    effective_to: datetime | None
    product: str
    channel: str
    jurisdiction: str
    source_type: PolicySourceType
    ingestion_run_id: UUID
    correlation_id: str
    chunks: list[PolicyChunkOut] = Field(default_factory=list)


class PolicyAuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_event_id: UUID
    ingestion_run_id: UUID | None
    document_id: str | None
    version: str | None
    checksum_sha256: str | None
    event_type: str
    actor_ref: str
    source: str
    decision_status: str
    event_metadata: dict[str, object]
    correlation_id: str
    created_at: datetime


class PolicyIngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    status: str
    actor_ref: str
    source: str
    parser_version: str
    chunking_config_hash: str
    embedding_model: str
    embedding_config_hash: str
    retrieval_index_config_hash: str
    correlation_id: str
    validation_errors: list[dict[str, object]] = Field(default_factory=list)
    telemetry: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None
    documents: list[PolicyDocumentOut] = Field(default_factory=list)
    audit_events: list[PolicyAuditEventOut] = Field(default_factory=list)


class PolicyPromotionRequest(BaseModel):
    ingestion_run_id: UUID
    actor_ref: str = Field(default="policy-admin", min_length=1, max_length=100)
    corpus_version: str = Field(min_length=1, max_length=80)
    index_version: str = Field(min_length=1, max_length=80)


class PolicyEvaluationOut(BaseModel):
    evaluation_id: UUID
    ingestion_run_id: UUID
    corpus_version: str
    index_version: str
    passed: bool
    metrics: dict[str, object]
    threshold_failures: list[dict[str, object]]
    correlation_id: str
    evaluated_at: datetime


class PolicyPromotionResponse(BaseModel):
    promoted: bool
    corpus_version: str
    index_version: str
    ingestion_run_id: UUID
    evaluation: PolicyEvaluationOut
    active_corpus_version: str | None
    correlation_id: str


class PolicyLineageResponse(BaseModel):
    chunk_id: str
    document_id: str
    version: str
    section: str
    effective_from: datetime
    effective_to: datetime | None
    ingestion_run_id: UUID
    source_checksum_sha256: str
    chunk_hash: str
    corpus_version: str | None
    index_version: str | None
    correlation_id: str


def parse_if_match(value: str) -> int:
    normalized = value.strip()
    match = re.fullmatch(r'(?:W/)?"?(\d+)"?', normalized)
    if match is None:
        raise ValueError("If-Match must contain a positive integer case version")
    version = int(match.group(1))
    if version < 1:
        raise ValueError("If-Match must contain a positive integer case version")
    return version
