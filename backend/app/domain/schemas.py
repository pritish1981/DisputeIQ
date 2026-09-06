from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


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


class ClassificationCategory(StrEnum):
    duplicate_card_transaction = "duplicate_card_transaction"
    failed_upi_transfer = "failed_upi_transfer"
    atm_debit_without_cash = "atm_debit_without_cash"
    unsupported = "unsupported"


class ModelGatewayStatus(StrEnum):
    accepted = "accepted"
    bypassed = "bypassed"
    failed = "failed"


class ModelGatewayFailureReason(StrEnum):
    ai_kill_switch = "ai_kill_switch"
    missing_configuration = "missing_configuration"
    token_budget_exceeded = "token_budget_exceeded"
    data_policy_violation = "data_policy_violation"
    provider_timeout = "provider_timeout"
    provider_error = "provider_error"
    schema_validation_failed = "schema_validation_failed"
    unsupported_category = "unsupported_category"
    low_confidence = "low_confidence"


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


class PolicyRetrievalAbstentionReason(StrEnum):
    missing_active_corpus = "missing_active_corpus"
    no_eligible_candidates = "no_eligible_candidates"
    low_confidence = "low_confidence"
    ambiguous_results = "ambiguous_results"
    missing_citation = "missing_citation"


class PolicyRetrievalConfig(BaseModel):
    version: str = Field(default="retrieval-config-v1", min_length=1, max_length=80)
    lexical_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.55, ge=0.0, le=1.0)
    top_k: int = Field(default=3, ge=1, le=20)
    minimum_confidence: float = Field(default=0.35, ge=0.0, le=1.0)
    ambiguity_threshold: float = Field(default=0.03, ge=0.0, le=1.0)
    require_citations: bool = True
    reranker_mode: str = Field(default="deterministic-fused-score-v1", min_length=1, max_length=80)

    @field_validator("vector_weight")
    @classmethod
    def validate_weight_sum(cls, value: float, info: ValidationInfo) -> float:
        lexical_weight = info.data.get("lexical_weight", 0.45)
        if abs(float(lexical_weight) + value - 1.0) > 0.000001:
            raise ValueError("lexical_weight and vector_weight must sum to 1.0")
        return value


class PolicyRetrievalRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    dispute_type: DisputeType = DisputeType.duplicate_card_transaction
    effective_date: datetime
    product: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=80)
    jurisdiction: str = Field(min_length=1, max_length=80)
    actor_ref: str = Field(default="policy-retrieval-service", min_length=1, max_length=100)
    case_id: UUID | None = None
    workflow_id: UUID | None = None
    dispute_metadata: dict[str, object] = Field(default_factory=dict)
    retrieval_config: PolicyRetrievalConfig = Field(default_factory=PolicyRetrievalConfig)

    @field_validator("effective_date")
    @classmethod
    def normalize_effective_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class PolicyCitationOut(BaseModel):
    document_id: str
    version: str
    section: str
    chunk_id: str
    chunk_hash: str
    effective_from: datetime
    effective_to: datetime | None
    ingestion_run_id: UUID
    corpus_version: str
    index_version: str


class PolicyRetrievedChunkOut(BaseModel):
    rank: int
    chunk_id: str
    content: str
    lexical_score: float
    vector_score: float
    fused_score: float
    reranker_mode: str
    citation: PolicyCitationOut


class PolicyReviewSignalOut(BaseModel):
    required: bool
    reason: PolicyRetrievalAbstentionReason | None = None
    message: str | None = None


class PolicyRetrievalTelemetryOut(BaseModel):
    case_id: UUID | None
    workflow_id: UUID | None
    correlation_id: str
    corpus_version: str | None
    index_version: str | None
    retrieval_config_version: str
    eligible_candidate_count: int
    returned_result_count: int
    confidence: float
    abstention_reason: PolicyRetrievalAbstentionReason | None
    latency_ms: int


class PolicyRetrievalResponse(BaseModel):
    status: str
    approved_context: bool
    requires_policy_review: bool
    confidence: float
    abstention_reason: PolicyRetrievalAbstentionReason | None = None
    policy_review: PolicyReviewSignalOut
    results: list[PolicyRetrievedChunkOut] = Field(default_factory=list)
    corpus_version: str | None
    index_version: str | None
    retrieval_config: PolicyRetrievalConfig
    correlation_id: str
    audit_event_id: UUID
    telemetry: PolicyRetrievalTelemetryOut


class PolicyRetrievalEvaluationRequest(BaseModel):
    actor_ref: str = Field(default="policy-admin:retrieval-eval", min_length=1, max_length=100)
    retrieval_config: PolicyRetrievalConfig = Field(default_factory=PolicyRetrievalConfig)


class PolicyRetrievalEvaluationResponse(BaseModel):
    accepted: bool
    corpus_version: str | None
    index_version: str | None
    retrieval_config_version: str
    evaluation: PolicyEvaluationOut
    correlation_id: str


class PromptReference(BaseModel):
    prompt_id: str = Field(default="classification-router", min_length=1, max_length=80)
    prompt_version: str = Field(default="classification-router-v1", min_length=1, max_length=80)
    template_hash: str = Field(default="classification-template-v1", min_length=1, max_length=120)


class ModelRouteConfig(BaseModel):
    route_version: str = Field(default="model-route-classification-v1", min_length=1, max_length=80)
    primary_provider: str = Field(default="deterministic-local", min_length=1, max_length=80)
    fallback_provider: str | None = Field(default="deterministic-fallback", max_length=80)
    model_ref: str = Field(default="local-classifier-v1", min_length=1, max_length=120)
    token_budget: int = Field(default=1200, ge=1, le=20000)
    timeout_ms: int = Field(default=2000, ge=1, le=60000)
    retry_limit: int = Field(default=1, ge=0, le=5)
    enabled: bool = True


class ModelGatewayRequest(BaseModel):
    capability: str = Field(min_length=1, max_length=80)
    case_id: UUID | None = None
    workflow_id: UUID | None = None
    correlation_id: str = Field(min_length=1, max_length=100)
    prompt: PromptReference = Field(default_factory=PromptReference)
    route: ModelRouteConfig = Field(default_factory=ModelRouteConfig)
    response_schema_version: str = Field(
        default="classification-output-v1", min_length=1, max_length=80
    )
    input_text: str = Field(min_length=1, max_length=8000)
    untrusted_inputs: dict[str, object] = Field(default_factory=dict)


class ModelGatewayProviderResult(BaseModel):
    provider_ref: str = Field(min_length=1, max_length=80)
    status: str = Field(min_length=1, max_length=40)
    output_json: dict[str, object] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: int = Field(default=0, ge=0)
    error_code: str | None = None


class ModelGatewayTelemetry(BaseModel):
    capability: str
    case_id: UUID | None
    workflow_id: UUID | None
    correlation_id: str
    provider_route_ref: str
    prompt_version: str
    schema_version: str
    latency_ms: int
    token_usage: dict[str, int] = Field(default_factory=dict)
    attempt_count: int
    fallback_used: bool
    kill_switch_enabled: bool
    status: ModelGatewayStatus
    failure_reason: ModelGatewayFailureReason | None = None


class ModelGatewayResponse(BaseModel):
    status: ModelGatewayStatus
    validated_output: dict[str, object] = Field(default_factory=dict)
    failure_reason: ModelGatewayFailureReason | None = None
    provider_ref: str | None = None
    fallback_used: bool = False
    attempt_count: int = 0
    route_version: str
    prompt_version: str
    schema_version: str
    token_usage: dict[str, int] = Field(default_factory=dict)
    telemetry: ModelGatewayTelemetry


class ClassificationAttributes(BaseModel):
    transaction_ref: str | None = None
    dispute_channel: str | None = None
    evidence_signal: str | None = None
    customer_signal: str | None = None


class ClassificationOutput(BaseModel):
    category: ClassificationCategory
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_attributes: ClassificationAttributes = Field(
        default_factory=ClassificationAttributes
    )
    schema_version: str = Field(default="classification-output-v1", min_length=1, max_length=80)
    prompt_version: str = Field(default="classification-router-v1", min_length=1, max_length=80)
    model_route_version: str = Field(
        default="model-route-classification-v1", min_length=1, max_length=80
    )
    correlation_id: str = Field(min_length=1, max_length=100)


class ClassificationInput(BaseModel):
    case_id: UUID | None = None
    workflow_id: UUID | None = None
    description: str = Field(min_length=1, max_length=4000)
    dispute_type_hint: DisputeType | None = None
    channel: Channel | None = None
    transaction_ref: str | None = Field(default=None, max_length=80)
    evidence_count: int = Field(default=0, ge=0)
    correlation_id: str = Field(min_length=1, max_length=100)


class ClassificationDecision(BaseModel):
    accepted: bool
    output: ClassificationOutput | None = None
    manual_classification_required: bool = False
    reason: ModelGatewayFailureReason | None = None
    threshold: float
    telemetry: ModelGatewayTelemetry
    evaluation_metadata: dict[str, object] = Field(default_factory=dict)


class WorkflowStatus(StrEnum):
    running = "RUNNING"
    waiting_evidence = "WAITING_EVIDENCE"
    waiting_policy_review = "WAITING_POLICY_REVIEW"
    waiting_manual_classification = "WAITING_MANUAL_CLASSIFICATION"
    manual_processing = "MANUAL_PROCESSING"
    controlled_stop = "CONTROLLED_STOP"
    completed = "COMPLETED"
    failed = "FAILED"


class WorkflowFailureKind(StrEnum):
    retriable = "retriable"
    manual_degradation = "manual_degradation"
    validation = "validation"
    fatal = "fatal"


class WorkflowStartRequest(BaseModel):
    case_id: UUID
    actor_ref: str = Field(default="workflow-service", min_length=1, max_length=100)
    graph_version: str = Field(default="duplicate-card-workflow-v1", min_length=1, max_length=80)


class WorkflowResumeRequest(BaseModel):
    actor_ref: str = Field(default="workflow-service", min_length=1, max_length=100)
    resume_reason: str = Field(default="authorized_resume", min_length=1, max_length=120)
    resume_payload: dict[str, object] = Field(default_factory=dict)


class WorkflowInterruptOut(BaseModel):
    required: bool = False
    reason: str | None = None
    message: str | None = None
    resume_requirements: list[str] = Field(default_factory=list)


class WorkflowCheckpointOut(BaseModel):
    checkpoint_id: UUID
    checkpoint_seq: int
    state_version: int
    current_node: str
    status: WorkflowStatus
    state_hash: str
    interrupt_reason: str | None = None
    side_effect_keys: list[str] = Field(default_factory=list)
    telemetry: dict[str, object] = Field(default_factory=dict)
    correlation_id: str
    created_at: datetime


class WorkflowTelemetryOut(BaseModel):
    case_id: UUID
    workflow_id: UUID
    graph_version: str
    current_node: str
    state_version: int
    correlation_id: str
    node_count: int
    checkpoint_count: int
    interrupt_count: int
    retry_count: int = 0
    status: WorkflowStatus
    latency_ms: int = 0


class WorkflowResponse(BaseModel):
    workflow_id: UUID
    case_id: UUID
    status: WorkflowStatus
    current_node: str
    state_version: int
    graph_version: str
    correlation_id: str
    checkpoint: WorkflowCheckpointOut | None = None
    interrupt: WorkflowInterruptOut = Field(default_factory=WorkflowInterruptOut)
    stage_summaries: dict[str, object] = Field(default_factory=dict)
    error_metadata: list[dict[str, object]] = Field(default_factory=list)
    telemetry: WorkflowTelemetryOut
    replayed: bool = False


def validate_workflow_state_payload(state: dict[str, object]) -> dict[str, object]:
    forbidden_keys = {
        "provider_payloads",
        "raw_provider_payload",
        "raw_provider_payloads",
        "hidden_reasoning",
        "evidence_binary",
        "evidence_binaries",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
    if len(str(state)) > 20000:
        raise ValueError("workflow state payload is too large")
    lowered: set[str] = set()

    def collect_keys(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                lowered.add(str(key).lower())
                collect_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_keys(nested)

    collect_keys(state)
    blocked = lowered & forbidden_keys
    if blocked:
        blocked_fields = ", ".join(sorted(blocked))
        raise ValueError(f"workflow state contains disallowed field(s): {blocked_fields}")
    return state


def parse_if_match(value: str) -> int:
    normalized = value.strip()
    match = re.fullmatch(r'(?:W/)?"?(\d+)"?', normalized)
    if match is None:
        raise ValueError("If-Match must contain a positive integer case version")
    version = int(match.group(1))
    if version < 1:
        raise ValueError("If-Match must contain a positive integer case version")
    return version
