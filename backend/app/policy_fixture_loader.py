from __future__ import annotations

from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.domain.schemas import (
    PolicyDocumentIn,
    PolicyIngestionRequest,
    PolicyPromotionRequest,
    PolicySectionIn,
    PolicyStatus,
)
from app.services.policy_ingestion import PolicyIngestionService


def synthetic_duplicate_card_policy_request() -> PolicyIngestionRequest:
    return PolicyIngestionRequest(
        actor_ref="policy-admin:fixture-loader",
        parser_version="parser-v1",
        chunking_config_hash="chunking-v1",
        embedding_model="deterministic-test-embedding-v1",
        embedding_config_hash="embedding-v1",
        retrieval_index_config_hash="retrieval-v1",
        documents=[
            PolicyDocumentIn(
                document_id="POL-DUPLICATE-CARD-SYNTHETIC",
                version="2026.09",
                title="Synthetic Duplicate Card Dispute Policy",
                status=PolicyStatus.approved,
                approval_ref="approval:synthetic-2026-09",
                source_identity="docs/source-of-truth/synthetic-policy-fixture",
                source_checksum_sha256="1" * 64,
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                product="card",
                channel="web",
                jurisdiction="US",
                sections=[
                    PolicySectionIn(
                        section="7.5.1",
                        text="Duplicate card disputes require matching transaction context.",
                    ),
                    PolicySectionIn(
                        section="7.5.2",
                        text="Policy-grounded recommendations require document version citations.",
                    ),
                ],
            )
        ],
    )


def load_and_promote_synthetic_policy() -> dict[str, object]:
    with SessionLocal() as session:
        service = PolicyIngestionService(session)
        run = service.ingest(
            synthetic_duplicate_card_policy_request(),
            correlation_id="corr-policy-fixture-loader",
        )
        promotion = service.promote(
            PolicyPromotionRequest(
                ingestion_run_id=run.run_id,
                actor_ref="policy-admin:fixture-loader",
                corpus_version="synthetic-policy-corpus-2026-09",
                index_version="synthetic-policy-index-2026-09",
            ),
            correlation_id="corr-policy-fixture-loader",
        )
        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "corpus_version": promotion.corpus_version,
            "index_version": promotion.index_version,
            "promoted": promotion.promoted,
            "correlation_id": promotion.correlation_id,
        }


if __name__ == "__main__":
    print(load_and_promote_synthetic_policy())
