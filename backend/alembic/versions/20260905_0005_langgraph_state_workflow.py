"""langgraph state workflow

Revision ID: 20260905_0005
Revises: 20260903_0003
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0005"
down_revision: str | None = "20260903_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("workflow_id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("graph_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_node", sa.String(length=120), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checkpoint_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interrupt_reason", sa.String(length=120), nullable=True),
        sa.Column("telemetry", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("started_by", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"]),
    )
    op.create_index("ix_workflow_runs_case_status", "workflow_runs", ["case_id", "status"])
    op.create_index("ix_workflow_runs_correlation", "workflow_runs", ["correlation_id"])
    op.execute(
        "CREATE UNIQUE INDEX uq_workflow_active_case "
        "ON workflow_runs (case_id) "
        "WHERE status IN ('RUNNING', 'WAITING_EVIDENCE', 'WAITING_POLICY_REVIEW', "
        "'WAITING_MANUAL_CLASSIFICATION', 'MANUAL_PROCESSING', 'CONTROLLED_STOP')"
    )

    op.create_table(
        "workflow_checkpoints",
        sa.Column("checkpoint_id", sa.String(length=36), primary_key=True),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("checkpoint_seq", sa.Integer(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("current_node", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("interrupt_reason", sa.String(length=120), nullable=True),
        sa.Column("side_effect_keys", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("telemetry", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_runs.workflow_id"]),
    )
    op.create_index(
        "uq_workflow_checkpoint_seq",
        "workflow_checkpoints",
        ["workflow_id", "checkpoint_seq"],
        unique=True,
    )
    op.create_index(
        "ix_workflow_checkpoint_state",
        "workflow_checkpoints",
        ["workflow_id", "state_version"],
    )
    op.create_index(
        "ix_workflow_checkpoint_created",
        "workflow_checkpoints",
        ["workflow_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_checkpoint_created", table_name="workflow_checkpoints")
    op.drop_index("ix_workflow_checkpoint_state", table_name="workflow_checkpoints")
    op.drop_index("uq_workflow_checkpoint_seq", table_name="workflow_checkpoints")
    op.drop_table("workflow_checkpoints")
    op.execute("DROP INDEX IF EXISTS uq_workflow_active_case")
    op.drop_index("ix_workflow_runs_correlation", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_case_status", table_name="workflow_runs")
    op.drop_table("workflow_runs")
