"""Validate Phase 007 admission in live PostgreSQL; predicate mutations are rolled back."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.models import PolicyChunkModel, PolicyDocumentModel
from app.control_regression import load_profile
from app.domain.schemas import PolicyRetrievalRequest
from app.services.policy_eligibility import PolicyEligibilityService
from app.services.policy_retrieval import PolicyRetrievalService


def verify_sql_admission(db: Session) -> list[str]:
    retrieval = PolicyRetrievalService(db, auto_commit=False)
    repository = retrieval.repository
    corpus = repository.active_corpus()
    assert corpus
    request = PolicyRetrievalRequest(
        query="duplicate card transaction issuer review evidence merchant context",
        effective_date=datetime(2026, 8, 28, tzinfo=UTC),
        product="card",
        channel="web",
        jurisdiction="US",
        actor_ref="test:sql-controls",
    )
    profile = load_profile().eligibility
    completed = []
    predicates: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        ("product", {"product": "upi"}, {}),
        ("channel", {"channel": "mobile"}, {}),
        ("jurisdiction", {"jurisdiction": "IN"}, {}),
        ("inactive", {"status": "revoked"}, {}),
        ("unapproved", {}, {"approval_ref": ""}),
        ("ineffective", {"effective_to": datetime(2025, 1, 1, tzinfo=UTC)}, {}),
        ("unmapped_family", {"document_id": "OTHER-FAMILY"}, {}),
        ("index_unready", {"vector_index_ready": False}, {}),
    ]
    for name, chunk_changes, document_changes in predicates:
        transaction = db.begin_nested()
        try:
            chunk = db.scalar(
                select(PolicyChunkModel)
                .where(
                    PolicyChunkModel.ingestion_run_id == corpus.ingestion_run_id,
                )
                .order_by(PolicyChunkModel.chunk_id)
            )
            assert chunk
            document = db.get(PolicyDocumentModel, chunk.policy_document_pk)
            assert document
            excluded_id = chunk.chunk_id
            for key, value in chunk_changes.items():
                setattr(chunk, key, value)
            for key, value in document_changes.items():
                setattr(document, key, value)
            db.flush()
            eligibility = PolicyEligibilityService().evaluate(repository, corpus, request, profile)
            assert excluded_id not in eligibility["eligible_chunk_ids"], name
            query_embedding = retrieval._format_vector(
                retrieval.embedding_adapter.embed(request.query)
            )
            rows = repository.hybrid_retrieve(
                corpus=corpus,
                query=request.query,
                query_embedding=query_embedding,
                effective_date=request.effective_date,
                product=request.product,
                channel=request.channel,
                jurisdiction=request.jurisdiction,
                limit=10,
                eligible_chunk_ids=eligibility["eligible_chunk_ids"],
            )
            assert excluded_id not in {row.chunk.chunk_id for row in rows}, name
            completed.append(name)
        finally:
            transaction.rollback()
            db.expire_all()
    # Inclusive effective-date boundary must remain admitted.
    chunk = db.scalar(
        select(PolicyChunkModel).where(
            PolicyChunkModel.ingestion_run_id == corpus.ingestion_run_id,
        )
    )
    assert chunk
    eligibility = PolicyEligibilityService().evaluate(
        repository,
        corpus,
        request.model_copy(update={"effective_date": chunk.effective_from}),
        profile,
    )
    assert chunk.chunk_id in eligibility["eligible_chunk_ids"]
    completed.append("effective_boundary_inclusive")
    return completed
