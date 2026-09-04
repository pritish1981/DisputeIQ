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


def synthetic_duplicate_card_policy_request(suffix: str = "") -> PolicyIngestionRequest:
    normalized_suffix = f"-{suffix}" if suffix else ""
    return PolicyIngestionRequest(
        actor_ref="policy-admin:fixture-loader",
        parser_version="parser-v1",
        chunking_config_hash="chunking-v1",
        embedding_model="deterministic-test-embedding-v1",
        embedding_config_hash="embedding-v1",
        retrieval_index_config_hash="retrieval-v1",
        documents=[
            PolicyDocumentIn(
                document_id=f"POL-DUPLICATE-CARD-SYNTHETIC{normalized_suffix}",
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


def synthetic_duplicate_card_retrieval_request(suffix: str = "") -> PolicyIngestionRequest:
    normalized_suffix = f"-{suffix}" if suffix else ""
    return PolicyIngestionRequest(
        actor_ref="policy-admin:fixture-loader",
        parser_version="parser-v1",
        chunking_config_hash="chunking-v1",
        embedding_model="deterministic-test-embedding-v1",
        embedding_config_hash="embedding-v1",
        retrieval_index_config_hash="retrieval-v1",
        documents=[
            PolicyDocumentIn(
                document_id=f"POL-DUP-CARD{normalized_suffix}",
                version="2026.09",
                title="Synthetic Duplicate Card Retrieval Policy",
                status=PolicyStatus.approved,
                approval_ref="approval:synthetic-retrieval-2026-09",
                source_identity="docs/source-of-truth/synthetic-policy-retrieval-fixture",
                source_checksum_sha256="2" * 64,
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                product="card",
                channel="web",
                jurisdiction="US",
                sections=[
                    PolicySectionIn(
                        section="7.5.1",
                        text=(
                            "Duplicate card transaction disputes require issuer review, "
                            "transaction matching, and merchant context."
                        ),
                    ),
                    PolicySectionIn(
                        section="7.5.2",
                        text=(
                            "Approved evidence for duplicate card disputes includes "
                            "transaction records and merchant context citations."
                        ),
                    ),
                ],
            ),
            PolicyDocumentIn(
                document_id=f"POL-DUP-CARD-STALE{normalized_suffix}",
                version="2025.01",
                title="Stale Duplicate Card Retrieval Policy",
                status=PolicyStatus.approved,
                approval_ref="approval:synthetic-retrieval-2025-01",
                source_identity="docs/source-of-truth/synthetic-policy-retrieval-fixture-stale",
                source_checksum_sha256="3" * 64,
                effective_from=datetime(2025, 1, 1, tzinfo=UTC),
                effective_to=datetime(2025, 12, 31, tzinfo=UTC),
                product="card",
                channel="web",
                jurisdiction="US",
                sections=[
                    PolicySectionIn(
                        section="7.5.old",
                        text=(
                            "Duplicate card transaction disputes require issuer review, "
                            "transaction matching, and merchant context."
                        ),
                    )
                ],
            ),
            PolicyDocumentIn(
                document_id=f"POL-DUP-CARD-WRONG-PRODUCT{normalized_suffix}",
                version="2026.09",
                title="Wrong Product Retrieval Policy",
                status=PolicyStatus.approved,
                approval_ref="approval:synthetic-retrieval-wrong-product",
                source_identity="docs/source-of-truth/synthetic-policy-retrieval-fixture-upi",
                source_checksum_sha256="4" * 64,
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                product="upi",
                channel="web",
                jurisdiction="US",
                sections=[
                    PolicySectionIn(
                        section="7.5.upi",
                        text="Duplicate card wording appears here but must not match card policy.",
                    )
                ],
            ),
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
