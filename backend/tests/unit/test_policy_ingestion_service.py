from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.models import (
    PolicyAuditEventModel,
    PolicyDocumentModel,
    PolicyIngestionRunModel,
)
from app.adapters.repositories import AuditWriteError, PolicyAuditRepository
from app.domain.schemas import (
    PolicyDocumentIn,
    PolicyIngestionRequest,
    PolicyPromotionRequest,
    PolicySectionIn,
    PolicySourceType,
    PolicyStatus,
)
from app.services.policy_ingestion import PolicyIngestionService, PolicyValidationError


def policy_document(
    *,
    document_id: str = "POL-SVC-DUP",
    version: str = "1",
    status: PolicyStatus = PolicyStatus.approved,
    source_type: PolicySourceType = PolicySourceType.approved_policy,
) -> PolicyDocumentIn:
    return PolicyDocumentIn(
        document_id=document_id,
        version=version,
        title="Service duplicate-card policy",
        status=status,
        approval_ref="approval:svc",
        source_identity="synthetic-service-fixture",
        source_checksum_sha256="e" * 64,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        product="card",
        channel="web",
        jurisdiction="US",
        source_type=source_type,
        sections=[
            PolicySectionIn(section="A", text="First stable policy section."),
            PolicySectionIn(section="B", text="Second stable policy section."),
        ],
    )


def policy_request(document: PolicyDocumentIn) -> PolicyIngestionRequest:
    return PolicyIngestionRequest(
        actor_ref="policy-admin:service",
        documents=[document],
        parser_version="parser-v1",
        chunking_config_hash="chunking-v1",
        embedding_model="deterministic-test-embedding-v1",
        embedding_config_hash="embedding-v1",
        retrieval_index_config_hash="retrieval-v1",
    )


def test_deterministic_ingestion_chunks_and_lineage(db_session: Session) -> None:
    service = PolicyIngestionService(db_session)
    document = policy_document()
    request = policy_request(document)
    first_chunks = service._chunk_document(document, request)
    second_chunks = service._chunk_document(document, request)
    run = service.ingest(request, correlation_id="corr-svc")

    assert first_chunks == second_chunks
    assert len(run.documents[0].chunks) == 2
    assert run.documents[0].chunks[0].chunk_hash == first_chunks[0][3]
    assert run.documents[0].chunks[0].vector_index_ready is True
    assert run.documents[0].chunks[0].lexical_index_ready is True


def test_invalid_sources_raise_validation_and_record_audit(db_session: Session) -> None:
    service = PolicyIngestionService(db_session)
    request = policy_request(
        policy_document(
            status=PolicyStatus.draft,
            source_type=PolicySourceType.historical_case,
        )
    )

    with pytest.raises(PolicyValidationError) as exc_info:
        service.ingest(request, correlation_id="corr-invalid")

    assert {item["code"] for item in exc_info.value.errors} == {
        "NON_POLICY_SOURCE",
        "UNAPPROVED_OR_INACTIVE",
    }
    audit = db_session.scalar(select(PolicyAuditEventModel))
    run = db_session.scalar(select(PolicyIngestionRunModel))
    assert run is not None
    assert run.status == "failed_validation"
    assert audit is not None
    assert audit.event_type == "POLICY_INGESTION_REJECTED"


def test_promotion_denial_preserves_active_corpus(db_session: Session) -> None:
    service = PolicyIngestionService(db_session)
    good = service.ingest(
        policy_request(policy_document(document_id="POL-SVC-GOOD")),
        correlation_id="corr-good",
    )
    first = service.promote(
        PolicyPromotionRequest(
            ingestion_run_id=good.run_id,
            actor_ref="policy-admin:service",
            corpus_version="corpus-good",
            index_version="index-good",
        ),
        correlation_id="corr-promote-good",
    )
    assert first.promoted is True

    failed_request = policy_request(
        policy_document(document_id="POL-SVC-FAILED", status=PolicyStatus.inactive)
    )
    with pytest.raises(PolicyValidationError):
        service.ingest(failed_request, correlation_id="corr-failed")
    failed_run = db_session.scalar(
        select(PolicyIngestionRunModel).where(
            PolicyIngestionRunModel.status == "failed_validation"
        )
    )
    assert failed_run is not None
    blocked = service.promote(
        PolicyPromotionRequest(
            ingestion_run_id=failed_run.run_id,
            actor_ref="policy-admin:service",
            corpus_version="corpus-failed",
            index_version="index-failed",
        ),
        correlation_id="corr-promote-failed",
    )

    assert blocked.promoted is False
    assert blocked.active_corpus_version == "corpus-good"
    assert blocked.evaluation.threshold_failures


def test_reindex_run_records_configuration_change_and_requires_evaluation(
    db_session: Session,
) -> None:
    service = PolicyIngestionService(db_session)
    request = policy_request(policy_document(document_id="POL-REINDEX"))
    changed_config = request.model_copy(
        update={
            "parser_version": "parser-v2",
            "chunking_config_hash": "chunking-v2",
            "embedding_model": "deterministic-test-embedding-v2",
            "retrieval_index_config_hash": "retrieval-v2",
        }
    )

    run = service.create_reindex_run(changed_config, correlation_id="corr-reindex")
    promotion = service.promote(
        PolicyPromotionRequest(
            ingestion_run_id=run.run_id,
            actor_ref="policy-admin:service",
            corpus_version="corpus-reindex",
            index_version="index-reindex",
        ),
        correlation_id="corr-reindex-promote",
    )
    events = db_session.scalars(
        select(PolicyAuditEventModel).where(
            PolicyAuditEventModel.ingestion_run_id == str(run.run_id)
        )
    ).all()

    assert run.parser_version == "parser-v2"
    assert any(event.event_type == "POLICY_REINDEX_CREATED" for event in events)
    assert promotion.promoted is True
    assert promotion.evaluation.passed is True


def test_policy_audit_failure_rolls_back_successful_ingestion(db_session: Session) -> None:
    service = PolicyIngestionService(
        db_session,
        audit_repository=PolicyAuditRepository(db_session, fail_writes=True),
    )

    with pytest.raises(AuditWriteError):
        service.ingest(policy_request(policy_document()), correlation_id="corr-audit-fail")

    assert db_session.scalar(select(PolicyDocumentModel)) is None
