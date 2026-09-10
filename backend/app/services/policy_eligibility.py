"""Deterministic admission before either lexical or vector scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.adapters.models import PolicyChunkModel, PolicyCorpusVersionModel, PolicyDocumentModel
from app.adapters.repositories import PolicyRepository
from app.domain.controls import EligibilityProfile
from app.domain.schemas import PolicyRetrievalRequest


def db_utc(value: datetime) -> datetime:
    # SQLite test storage loses timezone information; PostgreSQL preserves it.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PolicyEligibilityService:
    def evaluate(
        self,
        repository: PolicyRepository,
        corpus: PolicyCorpusVersionModel,
        request: PolicyRetrievalRequest,
        profile: EligibilityProfile | None = None,
    ) -> dict[str, Any]:
        sql_eligible = {
            c.chunk_id
            for c in repository.eligible_chunks(
                corpus=corpus,
                effective_date=request.effective_date,
                product=request.product,
                channel=request.channel,
                jurisdiction=request.jurisdiction,
            )
        }
        decisions = []
        admitted = []
        mapped = (
            {
                (p.document_id, p.version)
                for p in profile.mappings
                if (p.dispute_type == request.dispute_type.value and p.family == profile.family)
            }
            if profile
            else None
        )
        expected_product = {
            "duplicate_card_transaction": "card",
            "failed_upi_transfer": "upi",
            "atm_debit_without_cash": "atm",
        }.get(request.dispute_type.value)
        for chunk in repository.db.scalars(
            select(PolicyChunkModel)
            .where(PolicyChunkModel.ingestion_run_id == corpus.ingestion_run_id)
            .order_by(PolicyChunkModel.chunk_id)
        ):
            reasons = []
            document = repository.db.get(PolicyDocumentModel, chunk.policy_document_pk)
            if expected_product != request.product:
                reasons.append("DISPUTE_PRODUCT_MISMATCH")
            if mapped is not None and (chunk.document_id, chunk.version) not in mapped:
                reasons.append("POLICY_FAMILY_NOT_MAPPED")
            if (
                not document
                or document.status not in {"approved", "active"}
                or (not document.approval_ref)
            ):
                reasons.append("POLICY_NOT_APPROVED")
            if chunk.status not in {"approved", "active"}:
                reasons.append("CHUNK_NOT_ACTIVE")
            if chunk.product != request.product:
                reasons.append("PRODUCT_MISMATCH")
            if chunk.channel != request.channel:
                reasons.append("CHANNEL_MISMATCH")
            if chunk.jurisdiction != request.jurisdiction:
                reasons.append("JURISDICTION_MISMATCH")
            if db_utc(chunk.effective_from) > request.effective_date or (
                chunk.effective_to and db_utc(chunk.effective_to) < request.effective_date
            ):
                reasons.append("POLICY_NOT_EFFECTIVE")
            if document and (
                db_utc(document.effective_from) > request.effective_date
                or (
                    document.effective_to and db_utc(document.effective_to) < request.effective_date
                )
            ):
                reasons.append("DOCUMENT_NOT_EFFECTIVE")
            if chunk.chunk_id not in sql_eligible and not reasons:
                reasons.append("INDEX_NOT_READY")
            if not reasons:
                admitted.append(chunk.chunk_id)
            decisions.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "version": chunk.version,
                    "eligible": not reasons,
                    "reasons": reasons or ["ELIGIBLE"],
                }
            )
        return {
            "version": profile.version if profile else "metadata-eligibility-v1",
            "corpus_version": corpus.corpus_version,
            "eligible_chunk_ids": admitted,
            "inputs": {
                "product": request.product,
                "channel": request.channel,
                "jurisdiction": request.jurisdiction,
                "dispute_type": request.dispute_type.value,
                "effective_as_of": request.effective_date.isoformat(),
            },
            "decisions": decisions,
        }
