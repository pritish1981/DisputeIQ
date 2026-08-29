"""platform foundation

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("case_id", sa.String(length=36), primary_key=True),
        sa.Column("customer_ref", sa.String(length=80), nullable=False),
        sa.Column("account_ref", sa.String(length=80), nullable=True),
        sa.Column("transaction_ref", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("dispute_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cases_transaction_ref", "cases", ["transaction_ref"])
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("cases.case_id"), nullable=True),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_idempotency_operation_key",
        "idempotency_records",
        ["operation", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "timeline_entries",
        sa.Column("timeline_entry_id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("audit_event_id", sa.String(length=36), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_timeline_case_time", "timeline_entries", ["case_id", "occurred_at"])

    op.create_table(
        "evidence_metadata",
        sa.Column("evidence_id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploader_ref", sa.String(length=80), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_case", "evidence_metadata", ["case_id"])

    op.create_table(
        "provider_context",
        sa.Column("provider_context_id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("source_record_ref", sa.String(length=120), nullable=False),
        sa.Column("record_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("response_hash", sa.String(length=64), nullable=False),
        sa.Column("response_version", sa.String(length=40), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_context_case", "provider_context", ["case_id"])

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_ref", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("object_ref", sa.String(length=120), nullable=True),
        sa.Column("before_hash", sa.String(length=64), nullable=True),
        sa.Column("after_hash", sa.String(length=64), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_case_time", "audit_events", ["case_id", "created_at"])
    op.create_index("ix_audit_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_event_type", table_name="audit_events")
    op.drop_index("ix_audit_case_time", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_provider_context_case", table_name="provider_context")
    op.drop_table("provider_context")
    op.drop_index("ix_evidence_case", table_name="evidence_metadata")
    op.drop_table("evidence_metadata")
    op.drop_index("ix_timeline_case_time", table_name="timeline_entries")
    op.drop_table("timeline_entries")
    op.drop_index("uq_idempotency_operation_key", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_transaction_ref", table_name="cases")
    op.drop_table("cases")
