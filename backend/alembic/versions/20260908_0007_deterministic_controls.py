"""Immutable deterministic controls, evaluations and review requests."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_0007"
down_revision: str | None = "20260905_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "control_config_versions",
    "control_evaluations",
    "evidence_assessments",
    "policy_eligibility_evaluations",
    "rule_executions",
    "case_confidence_evaluations",
    "control_review_requests",
    "control_request_fulfillments",
    "evidence_validations",
)


def upgrade() -> None:
    op.create_table(
        "control_config_versions",
        sa.Column("config_id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(100), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("regression", sa.JSON(), nullable=False),
        sa.Column("actor_ref", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_control_profile_version",
        "control_config_versions",
        ["profile_id", "version"],
        unique=True,
    )
    op.create_table(
        "control_evaluations",
        sa.Column("evaluation_id", sa.String(36), primary_key=True),
        sa.Column(
            "workflow_id", sa.String(36), sa.ForeignKey("workflow_runs.workflow_id"), nullable=False
        ),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.String(36), sa.ForeignKey("control_config_versions.config_id")),
        sa.Column(
            "prior_evaluation_id", sa.String(36), sa.ForeignKey("control_evaluations.evaluation_id")
        ),
        sa.Column("bundle", sa.JSON(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("bundle_hash", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("actor_ref", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_control_workflow_state",
        "control_evaluations",
        ["workflow_id", "state_version"],
        unique=True,
    )
    for name in TABLES[2:6]:
        op.create_table(
            name,
            sa.Column("result_id", sa.String(36), primary_key=True),
            sa.Column(
                "evaluation_id",
                sa.String(36),
                sa.ForeignKey("control_evaluations.evaluation_id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("result_hash", sa.String(64), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    op.create_table(
        "control_review_requests",
        sa.Column("request_id", sa.String(36), primary_key=True),
        sa.Column(
            "evaluation_id",
            sa.String(36),
            sa.ForeignKey("control_evaluations.evaluation_id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("required_role", sa.String(80), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("required_items", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_control_review_type", "control_review_requests", ["evaluation_id", "kind"], unique=True
    )
    op.create_table(
        "control_request_fulfillments",
        sa.Column(
            "request_id",
            sa.String(36),
            sa.ForeignKey("control_review_requests.request_id"),
            primary_key=True,
        ),
        sa.Column(
            "evaluation_id",
            sa.String(36),
            sa.ForeignKey("control_evaluations.evaluation_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "evidence_validations",
        sa.Column(
            "evidence_id",
            sa.String(36),
            sa.ForeignKey("evidence_metadata.evidence_id"),
            primary_key=True,
        ),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("provenance", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_control_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Control records are append-only'; END;
        $$ LANGUAGE plpgsql""")
        for name in TABLES:
            op.execute(
                f"CREATE TRIGGER immutable_control BEFORE UPDATE OR DELETE ON {name} "
                "FOR EACH ROW EXECUTE FUNCTION reject_control_mutation()"
            )
        op.execute("DROP INDEX uq_workflow_active_case")
        op.execute(
            "CREATE UNIQUE INDEX uq_workflow_active_case ON workflow_runs(case_id) "
            "WHERE status NOT IN ('COMPLETED','FAILED')"
        )


def downgrade() -> None:
    # Operational rollback disables the graph; destructive downgrade requires an empty store.
    for name in TABLES:
        if op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {name}")):
            raise RuntimeError(
                "Cannot remove audited control records; disable graph starts instead"
            )
    for name in reversed(TABLES):
        op.drop_table(name)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_control_mutation()")
        op.execute("DROP INDEX uq_workflow_active_case")
        op.execute(
            "CREATE UNIQUE INDEX uq_workflow_active_case ON workflow_runs(case_id) "
            "WHERE status IN ('RUNNING', 'WAITING_EVIDENCE', 'WAITING_POLICY_REVIEW', "
            "'WAITING_MANUAL_CLASSIFICATION', 'MANUAL_PROCESSING', 'CONTROLLED_STOP')"
        )
