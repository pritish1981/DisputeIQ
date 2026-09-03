"""controlled policy ingestion

Revision ID: 20260903_0003
Revises: 20260830_0002
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0003"
down_revision: str | None = "20260830_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "policy_ingestion_runs",
        sa.Column("run_id", sa.String(length=36), primary_key=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("actor_ref", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("chunking_config_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=80), nullable=False),
        sa.Column("embedding_config_hash", sa.String(length=64), nullable=False),
        sa.Column("retrieval_index_config_hash", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("telemetry", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_policy_ingestion_runs_status", "policy_ingestion_runs", ["status"])
    op.create_index(
        "ix_policy_ingestion_runs_correlation",
        "policy_ingestion_runs",
        ["correlation_id"],
    )

    op.create_table(
        "policy_documents",
        sa.Column("policy_document_pk", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("approval_ref", sa.String(length=120), nullable=False),
        sa.Column("source_identity", sa.String(length=160), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("product", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("jurisdiction", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["policy_ingestion_runs.run_id"]),
    )
    op.create_index(
        "uq_policy_document_version",
        "policy_documents",
        ["document_id", "version"],
        unique=True,
    )
    op.create_index("ix_policy_documents_status", "policy_documents", ["status"])
    op.create_index("ix_policy_documents_run", "policy_documents", ["ingestion_run_id"])

    op.create_table(
        "policy_chunks",
        sa.Column("policy_chunk_pk", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_id", sa.String(length=120), nullable=False),
        sa.Column("policy_document_pk", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("section", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("product", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("jurisdiction", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("chunking_config_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=80), nullable=False),
        sa.Column("embedding_config_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_vector", sa.Text(), nullable=False),
        sa.Column("vector_index_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("lexical_index_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_document_pk"], ["policy_documents.policy_document_pk"]),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["policy_ingestion_runs.run_id"]),
    )
    op.execute(
        "ALTER TABLE policy_chunks ALTER COLUMN embedding_vector "
        "TYPE vector(8) USING embedding_vector::vector"
    )
    op.execute(
        "ALTER TABLE policy_chunks ADD COLUMN search_tsvector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )
    op.create_index("uq_policy_chunk", "policy_chunks", ["chunk_id"], unique=True)
    op.create_index(
        "ix_policy_chunks_document_version",
        "policy_chunks",
        ["document_id", "version"],
    )
    op.create_index("ix_policy_chunks_section", "policy_chunks", ["section"])
    op.create_index("ix_policy_chunks_ingestion_run", "policy_chunks", ["ingestion_run_id"])
    op.execute(
        "CREATE INDEX ix_policy_chunks_search_tsvector "
        "ON policy_chunks USING GIN (search_tsvector)"
    )
    op.execute(
        "CREATE INDEX ix_policy_chunks_embedding_vector "
        "ON policy_chunks USING hnsw (embedding_vector vector_cosine_ops)"
    )

    op.create_table(
        "policy_corpus_versions",
        sa.Column("corpus_version_id", sa.String(length=36), primary_key=True),
        sa.Column("corpus_version", sa.String(length=80), nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=False),
        sa.Column("index_version", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("promoted_by", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["policy_ingestion_runs.run_id"]),
    )
    op.create_index(
        "uq_policy_corpus_version",
        "policy_corpus_versions",
        ["corpus_version"],
        unique=True,
    )
    op.create_index("ix_policy_corpus_active", "policy_corpus_versions", ["is_active"])

    op.create_table(
        "policy_evaluation_results",
        sa.Column("evaluation_id", sa.String(length=36), primary_key=True),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=False),
        sa.Column("corpus_version", sa.String(length=80), nullable=False),
        sa.Column("index_version", sa.String(length=80), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("threshold_failures", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["policy_ingestion_runs.run_id"]),
    )
    op.create_index("ix_policy_eval_run", "policy_evaluation_results", ["ingestion_run_id"])

    op.create_table(
        "policy_audit_events",
        sa.Column("audit_event_id", sa.String(length=36), primary_key=True),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=True),
        sa.Column("document_id", sa.String(length=120), nullable=True),
        sa.Column("version", sa.String(length=40), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_ref", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("decision_status", sa.String(length=40), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_policy_audit_run_time",
        "policy_audit_events",
        ["ingestion_run_id", "created_at"],
    )
    op.create_index("ix_policy_audit_event_type", "policy_audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_policy_audit_event_type", table_name="policy_audit_events")
    op.drop_index("ix_policy_audit_run_time", table_name="policy_audit_events")
    op.drop_table("policy_audit_events")
    op.drop_index("ix_policy_eval_run", table_name="policy_evaluation_results")
    op.drop_table("policy_evaluation_results")
    op.drop_index("ix_policy_corpus_active", table_name="policy_corpus_versions")
    op.drop_index("uq_policy_corpus_version", table_name="policy_corpus_versions")
    op.drop_table("policy_corpus_versions")
    op.execute("DROP INDEX IF EXISTS ix_policy_chunks_embedding_vector")
    op.execute("DROP INDEX IF EXISTS ix_policy_chunks_search_tsvector")
    op.drop_index("ix_policy_chunks_ingestion_run", table_name="policy_chunks")
    op.drop_index("ix_policy_chunks_section", table_name="policy_chunks")
    op.drop_index("ix_policy_chunks_document_version", table_name="policy_chunks")
    op.drop_index("uq_policy_chunk", table_name="policy_chunks")
    op.drop_table("policy_chunks")
    op.drop_index("ix_policy_documents_run", table_name="policy_documents")
    op.drop_index("ix_policy_documents_status", table_name="policy_documents")
    op.drop_index("uq_policy_document_version", table_name="policy_documents")
    op.drop_table("policy_documents")
    op.drop_index("ix_policy_ingestion_runs_correlation", table_name="policy_ingestion_runs")
    op.drop_index("ix_policy_ingestion_runs_status", table_name="policy_ingestion_runs")
    op.drop_table("policy_ingestion_runs")
