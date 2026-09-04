from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.models import PolicyAuditEventModel, PolicyChunkModel
from app.adapters.repositories import PolicyAuditRepository
from app.domain.schemas import (
    PolicyDocumentIn,
    PolicyIngestionRequest,
    PolicyPromotionRequest,
    PolicyRetrievalAbstentionReason,
    PolicyRetrievalConfig,
    PolicyRetrievalEvaluationRequest,
    PolicyRetrievalRequest,
    PolicySectionIn,
    PolicyStatus,
)
from app.services.policy_ingestion import PolicyIngestionService
from app.services.policy_retrieval import PolicyRetrievalAuditError, PolicyRetrievalService


def policy_document(
    *,
    document_id: str = "POL-DUP-CARD",
    product: str = "card",
    channel: str = "web",
    jurisdiction: str = "US",
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    text: str = "Duplicate card transaction disputes require issuer review and merchant context.",
) -> PolicyDocumentIn:
    return PolicyDocumentIn(
        document_id=document_id,
        version="2026.09",
        title=f"{document_id} policy",
        status=PolicyStatus.approved,
        approval_ref=f"approval:{document_id}",
        source_identity=f"synthetic:{document_id}",
        source_checksum_sha256="a" * 64,
        effective_from=effective_from or datetime(2026, 1, 1, tzinfo=UTC),
        effective_to=effective_to,
        product=product,
        channel=channel,
        jurisdiction=jurisdiction,
        sections=[PolicySectionIn(section="7.5.1", text=text)],
    )


def retrieval_request(
    *,
    config: PolicyRetrievalConfig | None = None,
    product: str = "card",
    channel: str = "web",
    jurisdiction: str = "US",
    query: str = "duplicate card transaction issuer review merchant context",
) -> PolicyRetrievalRequest:
    return PolicyRetrievalRequest(
        query=query,
        effective_date=datetime(2026, 9, 4, tzinfo=UTC),
        product=product,
        channel=channel,
        jurisdiction=jurisdiction,
        actor_ref="policy-retrieval:test",
        retrieval_config=config or PolicyRetrievalConfig(ambiguity_threshold=0.0),
    )


def policy_ingestion_request(documents: list[PolicyDocumentIn]) -> PolicyIngestionRequest:
    return PolicyIngestionRequest(
        actor_ref="policy-admin:service",
        documents=documents,
        parser_version="parser-v1",
        chunking_config_hash="chunking-v1",
        embedding_model="deterministic-test-embedding-v1",
        embedding_config_hash="embedding-v1",
        retrieval_index_config_hash="retrieval-v1",
    )


def promote_documents(
    db_session: Session,
    documents: list[PolicyDocumentIn],
    *,
    corpus_version: str = "corpus-retrieval",
    index_version: str = "index-retrieval",
) -> None:
    ingestion = PolicyIngestionService(db_session)
    request = policy_ingestion_request(documents)
    run = ingestion.ingest(request, correlation_id="corr-ingest-retrieval")
    ingestion.promote(
        request=PolicyPromotionRequest(
            ingestion_run_id=run.run_id,
            actor_ref="policy-admin:test",
            corpus_version=corpus_version,
            index_version=index_version,
        ),
        correlation_id="corr-promote-retrieval",
    )


def test_retrieval_filters_before_ranking_and_returns_citation_lineage(
    db_session: Session,
) -> None:
    promote_documents(
        db_session,
        [
            policy_document(),
            policy_document(
                document_id="POL-DUP-CARD-STALE",
                effective_from=datetime(2025, 1, 1, tzinfo=UTC),
                effective_to=datetime(2025, 12, 31, tzinfo=UTC),
            ),
            policy_document(document_id="POL-DUP-CARD-UPI", product="upi"),
            policy_document(document_id="POL-DUP-CARD-BRANCH", channel="branch"),
            policy_document(document_id="POL-DUP-CARD-UK", jurisdiction="UK"),
        ],
    )
    result = PolicyRetrievalService(db_session).retrieve(
        retrieval_request(),
        correlation_id="corr-retrieve-success",
    )

    assert result.status == "retrieved"
    assert result.approved_context is True
    assert result.requires_policy_review is False
    assert result.corpus_version == "corpus-retrieval"
    assert result.index_version == "index-retrieval"
    assert result.retrieval_config.version == "retrieval-config-v1"
    assert result.telemetry.eligible_candidate_count == 1
    assert result.results[0].rank == 1
    assert result.results[0].lexical_score > 0
    assert result.results[0].vector_score > 0
    assert result.results[0].fused_score == result.confidence
    assert result.results[0].citation.document_id == "POL-DUP-CARD"
    assert result.results[0].citation.section == "7.5.1"
    assert result.audit_event_id is not None

    audit = db_session.scalar(
        select(PolicyAuditEventModel).where(
            PolicyAuditEventModel.event_type == "POLICY_RETRIEVAL_COMPLETED"
        )
    )
    assert audit is not None
    assert audit.event_metadata["selected_chunk_ids"] == [result.results[0].chunk_id]
    assert audit.event_metadata["retrieval_config_version"] == "retrieval-config-v1"


def test_retrieval_abstains_without_active_corpus(db_session: Session) -> None:
    result = PolicyRetrievalService(db_session).retrieve(
        retrieval_request(),
        correlation_id="corr-missing-corpus",
    )

    assert result.status == "abstained"
    assert result.abstention_reason == PolicyRetrievalAbstentionReason.missing_active_corpus
    assert result.requires_policy_review is True
    assert result.results == []


def test_retrieval_abstains_when_no_candidates_match_metadata(db_session: Session) -> None:
    promote_documents(db_session, [policy_document()])
    result = PolicyRetrievalService(db_session).retrieve(
        retrieval_request(product="deposit"),
        correlation_id="corr-no-candidates",
    )

    assert result.abstention_reason == PolicyRetrievalAbstentionReason.no_eligible_candidates
    assert result.telemetry.eligible_candidate_count == 0


def test_retrieval_abstains_for_low_confidence_and_ambiguous_results(
    db_session: Session,
) -> None:
    promote_documents(
        db_session,
        [
            policy_document(document_id="POL-DUP-CARD-A"),
            policy_document(document_id="POL-DUP-CARD-B"),
        ],
    )
    low_confidence = PolicyRetrievalService(db_session).retrieve(
        retrieval_request(config=PolicyRetrievalConfig(minimum_confidence=0.99)),
        correlation_id="corr-low-confidence",
    )
    ambiguous = PolicyRetrievalService(db_session).retrieve(
        retrieval_request(config=PolicyRetrievalConfig(ambiguity_threshold=1.0)),
        correlation_id="corr-ambiguous",
    )

    assert low_confidence.abstention_reason == PolicyRetrievalAbstentionReason.low_confidence
    assert ambiguous.abstention_reason == PolicyRetrievalAbstentionReason.ambiguous_results
    assert low_confidence.requires_policy_review is True
    assert ambiguous.requires_policy_review is True


def test_retrieval_abstains_when_citation_lineage_is_incomplete(
    db_session: Session,
) -> None:
    promote_documents(db_session, [policy_document()])
    chunk = db_session.scalar(select(PolicyChunkModel))
    assert chunk is not None
    chunk.chunk_hash = ""
    db_session.commit()

    result = PolicyRetrievalService(db_session).retrieve(
        retrieval_request(),
        correlation_id="corr-missing-citation",
    )

    assert result.abstention_reason == PolicyRetrievalAbstentionReason.missing_citation
    assert result.approved_context is False


def test_retrieval_audit_failure_blocks_successful_response(db_session: Session) -> None:
    promote_documents(db_session, [policy_document()])
    service = PolicyRetrievalService(
        db_session,
        audit_repository=PolicyAuditRepository(db_session, fail_writes=True),
    )

    with pytest.raises(PolicyRetrievalAuditError):
        service.retrieve(retrieval_request(), correlation_id="corr-audit-fail")

    assert db_session.scalar(
        select(PolicyAuditEventModel).where(
            PolicyAuditEventModel.event_type == "POLICY_RETRIEVAL_COMPLETED"
        )
    ) is None


def test_retrieval_regression_records_passing_and_failing_thresholds(
    db_session: Session,
) -> None:
    promote_documents(db_session, [policy_document()])
    service = PolicyRetrievalService(db_session)
    passing = service.evaluate(
        PolicyRetrievalEvaluationRequest(),
        correlation_id="corr-eval-pass",
    )
    failing = service.evaluate(
        PolicyRetrievalEvaluationRequest(
            retrieval_config=PolicyRetrievalConfig(minimum_confidence=0.99)
        ),
        correlation_id="corr-eval-fail",
    )

    assert passing.accepted is True
    assert passing.evaluation.metrics["retrieval_config_version"] == "retrieval-config-v1"
    assert failing.accepted is False
    assert {item["metric"] for item in failing.evaluation.threshold_failures} == {
        "retrieval_quality",
        "citation_correctness",
    }
