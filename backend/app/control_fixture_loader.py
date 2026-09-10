"""Local-only synthetic controls and explicitly validated evidence fixtures."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.models import CaseModel, EvidenceMetadataModel, EvidenceValidationModel
from app.adapters.repositories import AuditRepository
from app.control_regression import load_profile
from app.core.config import settings
from app.core.database import SessionLocal
from app.domain.schemas import PolicyIngestionRequest, PolicyPromotionRequest
from app.policy_fixture_loader import synthetic_duplicate_card_retrieval_request
from app.services.control_registry import ControlRegistry
from app.services.policy_ingestion import PolicyIngestionService

SYNTHETIC_STATEMENT = b"Synthetic duplicate-card statement: two charges for one purchase."
STATEMENT_CHECKSUM = hashlib.sha256(SYNTHETIC_STATEMENT).hexdigest()


def validate_synthetic_evidence(session: Session, case_id: str) -> None:
    if settings.app_env not in {"local", "test"}:
        raise ValueError("Synthetic evidence loader is local/test only")
    for item in session.scalars(
        select(EvidenceMetadataModel).where(
            EvidenceMetadataModel.case_id == case_id,
            EvidenceMetadataModel.checksum_sha256 == STATEMENT_CHECKSUM,
            EvidenceMetadataModel.evidence_type.in_(("receipt", "customer_statement")),
        )
    ):
        if session.get(EvidenceValidationModel, item.evidence_id) is None:
            session.add(
                EvidenceValidationModel(
                    evidence_id=item.evidence_id,
                    checksum=STATEMENT_CHECKSUM,
                    status="validated",
                    provenance="synthetic-fixture:controls-statement-v1:known-content",
                    created_at=datetime.now(UTC),
                )
            )
            case = session.get(CaseModel, case_id)
            if case is None:
                raise LookupError("Case not found")
            AuditRepository(session).append(
                case=case,
                event_type="EVIDENCE_VALIDATED",
                object_ref=item.evidence_id,
                state_version=case.state_version,
                correlation_id=item.correlation_id,
                metadata={
                    "evidence_id": item.evidence_id,
                    "checksum": STATEMENT_CHECKSUM,
                    "provenance": "synthetic-fixture:controls-statement-v1:known-content",
                },
                now=datetime.now(UTC),
            )
    session.flush()


def control_policy_request() -> PolicyIngestionRequest:
    document = synthetic_duplicate_card_retrieval_request().documents[0]
    return PolicyIngestionRequest(
        documents=[
            document.model_copy(
                update={
                    "document_id": "POL-DUP-CARD-CONTROLS",
                }
            )
        ]
    )


def load_control_fixtures(session: Session) -> dict[str, object]:
    if settings.app_env not in {"local", "test"}:
        raise ValueError("Synthetic controls loader is local/test only")
    registry = ControlRegistry(session).register(load_profile(), "control-admin:fixture-loader")
    session.commit()
    policy = PolicyIngestionService(session)
    existing = policy.repository.get_document("POL-DUP-CARD-CONTROLS", "2026.09")
    if existing is None:
        ingestion = policy.ingest(
            control_policy_request(), correlation_id="controls-policy-fixture"
        )
        run_id = ingestion.run_id
    else:
        from uuid import UUID

        run_id = UUID(existing.ingestion_run_id)
    active = policy.repository.active_corpus()
    if active is None or active.ingestion_run_id != str(run_id):
        from uuid import uuid4

        suffix = uuid4().hex[:10]
        policy.promote(
            PolicyPromotionRequest(
                ingestion_run_id=run_id,
                actor_ref="policy-admin:controls-loader",
                corpus_version=f"controls-corpus-{suffix}",
                index_version=f"controls-index-{suffix}",
            ),
            correlation_id="controls-policy-promotion",
        )
    return {
        "config_id": registry.config_id,
        "profile_version": registry.version,
        "statement_checksum": STATEMENT_CHECKSUM,
        "policy_run_id": str(run_id),
    }


if __name__ == "__main__":
    with SessionLocal() as db:
        print(load_control_fixtures(db))
