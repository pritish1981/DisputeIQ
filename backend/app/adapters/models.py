from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CaseModel(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    account_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transaction_ref: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    dispute_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.case_id"), nullable=True)
    response_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimelineEntryModel(Base):
    __tablename__ = "timeline_entries"

    timeline_entry_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    audit_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="timeline")


class EvidenceMetadataModel(Base):
    __tablename__ = "evidence_metadata"

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploader_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="evidence_metadata")


class ProviderContextModel(Base):
    __tablename__ = "provider_context"

    provider_context_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False, index=True)
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

    audit_event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    object_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    before_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="audit_events")
