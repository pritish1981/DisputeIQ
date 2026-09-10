"""Enforce control evaluation case/workflow and prior-evaluation scoping in storage."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260910_0007b"
down_revision: str | None = "20260908_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_workflow_case_scope", "workflow_runs", ["workflow_id", "case_id"]
    )
    op.create_unique_constraint(
        "uq_control_evaluation_scope", "control_evaluations", ["evaluation_id", "workflow_id"]
    )
    op.create_foreign_key(
        "fk_control_workflow_case",
        "control_evaluations",
        "workflow_runs",
        ["workflow_id", "case_id"],
        ["workflow_id", "case_id"],
    )
    op.create_foreign_key(
        "fk_control_prior_scope",
        "control_evaluations",
        "control_evaluations",
        ["prior_evaluation_id", "workflow_id"],
        ["evaluation_id", "workflow_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_control_prior_scope", "control_evaluations", type_="foreignkey")
    op.drop_constraint("fk_control_workflow_case", "control_evaluations", type_="foreignkey")
    op.drop_constraint("uq_control_evaluation_scope", "control_evaluations", type_="unique")
    op.drop_constraint("uq_workflow_case_scope", "workflow_runs", type_="unique")
