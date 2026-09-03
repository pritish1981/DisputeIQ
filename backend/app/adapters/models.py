from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CaseModel(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_ref: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    account_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transaction_ref: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    channel_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    dispute_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    timeline: Mapped[list[TimelineEntryModel]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    evidence_metadata: Mapped[list[EvidenceMetadataModel]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    provider_context: Mapped[list[ProviderContextModel]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[AuditEventModel]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        Index("uq_idempotency_operation_key", "operation", "idempotency_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.case_id"), nullable=True)
    response_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    replay_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_replayed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimelineEntryModel(Base):
    __tablename__ = "timeline_entries"
    __table_args__ = (Index("ix_timeline_case_time", "case_id", "occurred_at"),)

    timeline_entry_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    audit_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="timeline")


class EvidenceMetadataModel(Base):
    __tablename__ = "evidence_metadata"
    __table_args__ = (
        Index("ix_evidence_case", "case_id"),
        Index("ix_evidence_case_registered", "case_id", "registered_at"),
    )

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    uploader_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="evidence_metadata")


class ProviderContextModel(Base):
    __tablename__ = "provider_context"
    __table_args__ = (Index("ix_provider_context_case", "case_id"),)

    provider_context_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_record_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    record_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_version: Mapped[str] = mapped_column(String(40), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="provider_context")


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_case_time", "case_id", "created_at"),
        Index("ix_audit_event_type", "event_type"),
    )

    audit_event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    object_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    before_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="audit_events")


class PolicyIngestionRunModel(Base):
    __tablename__ = "policy_ingestion_runs"
    __table_args__ = (
        Index("ix_policy_ingestion_runs_status", "status"),
        Index("ix_policy_ingestion_runs_correlation", "correlation_id"),
    )

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(40), nullable=False)
    chunking_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_index_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    validation_errors: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    telemetry: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list[PolicyDocumentModel]] = relationship(
        back_populates="ingestion_run", cascade="all, delete-orphan"
    )


class PolicyDocumentModel(Base):
    __tablename__ = "policy_documents"
    __table_args__ = (
        Index("uq_policy_document_version", "document_id", "version", unique=True),
        Index("ix_policy_documents_status", "status"),
        Index("ix_policy_documents_run", "ingestion_run_id"),
    )

    policy_document_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    approval_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    source_identity: Mapped[str] = mapped_column(String(160), nullable=False)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    product: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_run_id: Mapped[str] = mapped_column(
        ForeignKey("policy_ingestion_runs.run_id"), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ingestion_run: Mapped[PolicyIngestionRunModel] = relationship(back_populates="documents")
    chunks: Mapped[list[PolicyChunkModel]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class PolicyChunkModel(Base):
    __tablename__ = "policy_chunks"
    __table_args__ = (
        Index("uq_policy_chunk", "chunk_id", unique=True),
        Index("ix_policy_chunks_document_version", "document_id", "version"),
        Index("ix_policy_chunks_section", "section"),
        Index("ix_policy_chunks_ingestion_run", "ingestion_run_id"),
    )

    policy_chunk_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(120), nullable=False)
    policy_document_pk: Mapped[int] = mapped_column(
        ForeignKey("policy_documents.policy_document_pk"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    section: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    product: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(40), nullable=False)
    chunking_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_vector: Mapped[str] = mapped_column(Text, nullable=False)
    vector_index_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lexical_index_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ingestion_run_id: Mapped[str] = mapped_column(
        ForeignKey("policy_ingestion_runs.run_id"), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document: Mapped[PolicyDocumentModel] = relationship(back_populates="chunks")


class PolicyCorpusVersionModel(Base):
    __tablename__ = "policy_corpus_versions"
    __table_args__ = (
        Index("uq_policy_corpus_version", "corpus_version", unique=True),
        Index("ix_policy_corpus_active", "is_active"),
    )

    corpus_version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    corpus_version: Mapped[str] = mapped_column(String(80), nullable=False)
    ingestion_run_id: Mapped[str] = mapped_column(
        ForeignKey("policy_ingestion_runs.run_id"), nullable=False
    )
    index_version: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promoted_by: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PolicyEvaluationResultModel(Base):
    __tablename__ = "policy_evaluation_results"
    __table_args__ = (Index("ix_policy_eval_run", "ingestion_run_id"),)

    evaluation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingestion_run_id: Mapped[str] = mapped_column(
        ForeignKey("policy_ingestion_runs.run_id"), nullable=False
    )
    corpus_version: Mapped[str] = mapped_column(String(80), nullable=False)
    index_version: Mapped[str] = mapped_column(String(80), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    threshold_failures: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PolicyAuditEventModel(Base):
    __tablename__ = "policy_audit_events"
    __table_args__ = (
        Index("ix_policy_audit_run_time", "ingestion_run_id", "created_at"),
        Index("ix_policy_audit_event_type", "event_type"),
    )

    audit_event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingestion_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    decision_status: Mapped[str] = mapped_column(String(40), nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
