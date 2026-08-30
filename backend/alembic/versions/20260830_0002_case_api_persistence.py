"""case API and persistence

Revision ID: 20260830_0002
Revises: 20260829_0001
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0002"
down_revision: str | None = "20260829_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column(
            "channel_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "cases",
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("cases", sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cases", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE cases SET opened_at = created_at WHERE opened_at IS NULL")
    op.alter_column("cases", "opened_at", nullable=False)
    op.create_index("ix_cases_customer_ref", "cases", ["customer_ref"])
    op.create_index("ix_cases_channel", "cases", ["channel"])
    op.create_index("ix_cases_opened_at", "cases", ["opened_at"])

    op.add_column(
        "idempotency_records",
        sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "idempotency_records",
        sa.Column("last_replayed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column(
        "idempotency_records",
        "operation",
        existing_type=sa.String(length=80),
        type_=sa.String(length=120),
    )

    op.add_column(
        "timeline_entries",
        sa.Column(
            "actor", sa.String(length=100), nullable=False, server_default="case-service"
        ),
    )
    op.add_column(
        "timeline_entries",
        sa.Column("source", sa.String(length=80), nullable=False, server_default="case-api"),
    )

    op.add_column(
        "evidence_metadata",
        sa.Column(
            "evidence_type", sa.String(length=80), nullable=False, server_default="other"
        ),
    )
    op.add_column(
        "evidence_metadata", sa.Column("object_ref", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "evidence_metadata",
        sa.Column(
            "source", sa.String(length=80), nullable=False, server_default="customer_upload"
        ),
    )
    op.add_column(
        "evidence_metadata",
        sa.Column(
            "status", sa.String(length=40), nullable=False, server_default="registered"
        ),
    )
    op.add_column(
        "evidence_metadata",
        sa.Column(
            "correlation_id",
            sa.String(length=100),
            nullable=False,
            server_default="migration",
        ),
    )
    op.add_column(
        "evidence_metadata",
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE evidence_metadata SET registered_at = uploaded_at WHERE registered_at IS NULL"
    )
    op.alter_column("evidence_metadata", "registered_at", nullable=False)
    op.drop_column("evidence_metadata", "uploaded_at")
    op.create_index(
        "ix_evidence_case_registered",
        "evidence_metadata",
        ["case_id", "registered_at"],
    )

    op.add_column(
        "audit_events",
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("audit_events", "state_version")
    op.drop_index("ix_evidence_case_registered", table_name="evidence_metadata")
    op.add_column(
        "evidence_metadata",
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE evidence_metadata SET uploaded_at = registered_at WHERE uploaded_at IS NULL"
    )
    op.alter_column("evidence_metadata", "uploaded_at", nullable=False)
    op.drop_column("evidence_metadata", "registered_at")
    op.drop_column("evidence_metadata", "correlation_id")
    op.drop_column("evidence_metadata", "status")
    op.drop_column("evidence_metadata", "source")
    op.drop_column("evidence_metadata", "object_ref")
    op.drop_column("evidence_metadata", "evidence_type")
    op.drop_column("timeline_entries", "source")
    op.drop_column("timeline_entries", "actor")
    op.alter_column(
        "idempotency_records",
        "operation",
        existing_type=sa.String(length=120),
        type_=sa.String(length=80),
    )
    op.drop_column("idempotency_records", "last_replayed_at")
    op.drop_column("idempotency_records", "replay_count")
    op.drop_index("ix_cases_opened_at", table_name="cases")
    op.drop_index("ix_cases_channel", table_name="cases")
    op.drop_index("ix_cases_customer_ref", table_name="cases")
    op.drop_column("cases", "closed_at")
    op.drop_column("cases", "opened_at")
    op.drop_column("cases", "state_version")
    op.drop_column("cases", "channel_metadata")
