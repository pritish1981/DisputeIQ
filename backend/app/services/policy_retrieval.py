from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.models import PolicyAuditEventModel
from app.adapters.repositories import (
    AuditWriteError,
    PolicyAuditRepository,
    PolicyRepository,
    PolicyRetrievalRow,
    utc_now,
)
from app.domain.controls import EligibilityProfile
from app.domain.schemas import (
    PolicyCitationOut,
    PolicyEvaluationOut,
    PolicyRetrievalAbstentionReason,
    PolicyRetrievalConfig,
    PolicyRetrievalEvaluationRequest,
    PolicyRetrievalEvaluationResponse,
    PolicyRetrievalRequest,
    PolicyRetrievalResponse,
    PolicyRetrievalTelemetryOut,
    PolicyRetrievedChunkOut,
    PolicyReviewSignalOut,
)
from app.services.policy_eligibility import PolicyEligibilityService
from app.services.policy_ingestion import DeterministicEmbeddingAdapter, PolicyAuthorizationError


class PolicyRetrievalAuditError(Exception):
    pass


@dataclass(frozen=True)
class _RankedPolicyRow:
    source: PolicyRetrievalRow
    rank: int
    fused_score: float


class PolicyRetrievalService:
    def __init__(
        self,
        db: Session,
        *,
        repository: PolicyRepository | None = None,
        audit_repository: PolicyAuditRepository | None = None,
        embedding_adapter: DeterministicEmbeddingAdapter | None = None,
        auto_commit: bool = True,
    ) -> None:
        self.db = db
        self.repository = repository or PolicyRepository(db)
        self.audit_repository = audit_repository or PolicyAuditRepository(db)
        self.embedding_adapter = embedding_adapter or DeterministicEmbeddingAdapter()
        self.auto_commit = auto_commit

    def retrieve(
        self,
        request: PolicyRetrievalRequest,
        *,
        correlation_id: str,
        eligibility_profile: EligibilityProfile | None = None,
    ) -> PolicyRetrievalResponse:
        self._validate_actor(request.actor_ref)
        started = perf_counter()
        now = utc_now()
        active = self.repository.active_corpus()
        if active is None:
            return self._abstain(
                request=request,
                reason=PolicyRetrievalAbstentionReason.missing_active_corpus,
                correlation_id=correlation_id,
                now=now,
                started=started,
                candidate_count=0,
                result_count=0,
                corpus_version=None,
                index_version=None,
            )

        eligibility = PolicyEligibilityService().evaluate(
            self.repository, active, request, eligibility_profile
        )
        eligible = eligibility["eligible_chunk_ids"]
        if not eligible:
            return self._abstain(
                request=request,
                reason=PolicyRetrievalAbstentionReason.no_eligible_candidates,
                correlation_id=correlation_id,
                now=now,
                started=started,
                candidate_count=0,
                result_count=0,
                corpus_version=active.corpus_version,
                index_version=active.index_version,
                eligibility=eligibility,
            )

        query_embedding = self._format_vector(self.embedding_adapter.embed(request.query))
        rows = self.repository.hybrid_retrieve(
            corpus=active,
            query=request.query,
            query_embedding=query_embedding,
            effective_date=request.effective_date,
            product=request.product,
            channel=request.channel,
            jurisdiction=request.jurisdiction,
            limit=request.retrieval_config.top_k,
            eligible_chunk_ids=eligible,
        )
        ranked = self._rank(rows, request.retrieval_config)
        if not ranked:
            return self._abstain(
                request=request,
                reason=PolicyRetrievalAbstentionReason.low_confidence,
                correlation_id=correlation_id,
                now=now,
                started=started,
                candidate_count=len(eligible),
                result_count=0,
                corpus_version=active.corpus_version,
                index_version=active.index_version,
                eligibility=eligibility,
            )

        citation_reason = self._citation_failure(ranked)
        if request.retrieval_config.require_citations and citation_reason is not None:
            return self._abstain(
                request=request,
                reason=citation_reason,
                correlation_id=correlation_id,
                now=now,
                started=started,
                candidate_count=len(eligible),
                result_count=len(ranked),
                corpus_version=active.corpus_version,
                index_version=active.index_version,
                eligibility=eligibility,
            )

        top_score = ranked[0].fused_score
        if top_score < request.retrieval_config.minimum_confidence:
            return self._abstain(
                request=request,
                reason=PolicyRetrievalAbstentionReason.low_confidence,
                correlation_id=correlation_id,
                now=now,
                started=started,
                candidate_count=len(eligible),
                result_count=len(ranked),
                corpus_version=active.corpus_version,
                index_version=active.index_version,
                eligibility=eligibility,
            )
        if self._is_ambiguous(ranked, request.retrieval_config):
            return self._abstain(
                request=request,
                reason=PolicyRetrievalAbstentionReason.ambiguous_results,
                correlation_id=correlation_id,
                now=now,
                started=started,
                candidate_count=len(eligible),
                result_count=len(ranked),
                corpus_version=active.corpus_version,
                index_version=active.index_version,
                eligibility=eligibility,
            )

        results = [
            self._chunk_out(
                row,
                active.corpus_version,
                active.index_version,
                request.retrieval_config,
            )
            for row in ranked
        ]
        telemetry = self._telemetry(
            request=request,
            correlation_id=correlation_id,
            corpus_version=active.corpus_version,
            index_version=active.index_version,
            candidate_count=len(eligible),
            result_count=len(results),
            confidence=top_score,
            abstention_reason=None,
            started=started,
        )
        event = self._audit(
            event_type="POLICY_RETRIEVAL_COMPLETED",
            actor_ref=request.actor_ref,
            decision_status="retrieved",
            correlation_id=correlation_id,
            now=now,
            ingestion_run_id=active.ingestion_run_id,
            metadata={
                "corpus_version": active.corpus_version,
                "index_version": active.index_version,
                "retrieval_config_version": request.retrieval_config.version,
                "selected_chunk_ids": [item.chunk_id for item in results],
                "document_versions": [
                    {
                        "document_id": item.citation.document_id,
                        "version": item.citation.version,
                        "section": item.citation.section,
                    }
                    for item in results
                ],
                "eligible_candidate_count": len(eligible),
                "returned_result_count": len(results),
                "confidence": top_score,
                "telemetry": telemetry.model_dump(mode="json"),
                "eligibility": eligibility,
            },
        )
        if self.auto_commit:
            self.db.commit()
        return PolicyRetrievalResponse(
            eligibility=eligibility,
            status="retrieved",
            approved_context=True,
            requires_policy_review=False,
            confidence=top_score,
            abstention_reason=None,
            policy_review=PolicyReviewSignalOut(required=False),
            results=results,
            corpus_version=active.corpus_version,
            index_version=active.index_version,
            retrieval_config=request.retrieval_config,
            correlation_id=correlation_id,
            audit_event_id=UUID(event.audit_event_id),
            telemetry=telemetry,
        )

    def evaluate(
        self,
        request: PolicyRetrievalEvaluationRequest,
        *,
        correlation_id: str,
    ) -> PolicyRetrievalEvaluationResponse:
        self._validate_actor(request.actor_ref)
        now = utc_now()
        active = self.repository.active_corpus()
        metrics: dict[str, object]
        failures: list[dict[str, object]]
        if active is None:
            metrics = {
                "retrieval_quality": 0.0,
                "citation_correctness": 0.0,
                "metadata_filtering": 0.0,
                "stale_policy_exclusion": 0.0,
            }
            failures = [
                {"metric": metric, "threshold": 1.0, "actual": value}
                for metric, value in metrics.items()
            ]
            return PolicyRetrievalEvaluationResponse(
                accepted=False,
                corpus_version=None,
                index_version=None,
                retrieval_config_version=request.retrieval_config.version,
                evaluation=PolicyEvaluationOut(
                    evaluation_id=UUID("00000000-0000-0000-0000-000000000000"),
                    ingestion_run_id=UUID("00000000-0000-0000-0000-000000000000"),
                    corpus_version="none",
                    index_version="none",
                    passed=False,
                    metrics={
                        **metrics,
                        "retrieval_config_version": request.retrieval_config.version,
                    },
                    threshold_failures=failures,
                    correlation_id=correlation_id,
                    evaluated_at=now,
                ),
                correlation_id=correlation_id,
            )
        else:
            retrieval = self.retrieve(
                self._duplicate_card_eval_request(request.retrieval_config, request.actor_ref),
                correlation_id=correlation_id,
            )
            selected_sections = {item.citation.section for item in retrieval.results}
            metrics = {
                "retrieval_quality": 1.0 if retrieval.approved_context else 0.0,
                "citation_correctness": 1.0 if selected_sections else 0.0,
                "metadata_filtering": 1.0
                if all(
                    item.citation.corpus_version == active.corpus_version
                    for item in retrieval.results
                )
                else 0.0,
                "stale_policy_exclusion": 1.0
                if all("STALE" not in item.citation.document_id for item in retrieval.results)
                else 0.0,
            }
            failures = [
                {"metric": metric, "threshold": 1.0, "actual": value}
                for metric, value in metrics.items()
                if value != 1.0
            ]
            ingestion_run_id = active.ingestion_run_id
            corpus_version = active.corpus_version
            index_version = active.index_version
        evaluation = self.repository.add_evaluation(
            ingestion_run_id=ingestion_run_id,
            corpus_version=corpus_version,
            index_version=index_version,
            passed=not failures,
            metrics={
                **metrics,
                "retrieval_config_version": request.retrieval_config.version,
            },
            threshold_failures=failures,
            correlation_id=correlation_id,
            now=now,
        )
        if self.auto_commit:
            self.db.commit()
        return PolicyRetrievalEvaluationResponse(
            accepted=not failures,
            corpus_version=None if corpus_version == "none" else corpus_version,
            index_version=None if index_version == "none" else index_version,
            retrieval_config_version=request.retrieval_config.version,
            evaluation=PolicyEvaluationOut(
                evaluation_id=UUID(evaluation.evaluation_id),
                ingestion_run_id=UUID(evaluation.ingestion_run_id),
                corpus_version=evaluation.corpus_version,
                index_version=evaluation.index_version,
                passed=evaluation.passed,
                metrics=evaluation.metrics,
                threshold_failures=evaluation.threshold_failures,
                correlation_id=evaluation.correlation_id,
                evaluated_at=evaluation.evaluated_at,
            ),
            correlation_id=correlation_id,
        )

    def _abstain(
        self,
        *,
        request: PolicyRetrievalRequest,
        reason: PolicyRetrievalAbstentionReason,
        correlation_id: str,
        now: datetime,
        started: float,
        candidate_count: int,
        result_count: int,
        corpus_version: str | None,
        index_version: str | None,
        eligibility: dict[str, Any] | None = None,
    ) -> PolicyRetrievalResponse:
        telemetry = self._telemetry(
            request=request,
            correlation_id=correlation_id,
            corpus_version=corpus_version,
            index_version=index_version,
            candidate_count=candidate_count,
            result_count=result_count,
            confidence=0.0,
            abstention_reason=reason,
            started=started,
        )
        event = self._audit(
            event_type="POLICY_RETRIEVAL_ABSTAINED",
            actor_ref=request.actor_ref,
            decision_status="policy_review_required",
            correlation_id=correlation_id,
            now=now,
            metadata={
                "abstention_reason": reason.value,
                "eligibility": eligibility or {},
                "corpus_version": corpus_version,
                "index_version": index_version,
                "retrieval_config_version": request.retrieval_config.version,
                "eligible_candidate_count": candidate_count,
                "returned_result_count": result_count,
                "requires_policy_review": True,
                "telemetry": telemetry.model_dump(mode="json"),
            },
        )
        if self.auto_commit:
            self.db.commit()
        return PolicyRetrievalResponse(
            eligibility=eligibility or {},
            status="abstained",
            approved_context=False,
            requires_policy_review=True,
            confidence=0.0,
            abstention_reason=reason,
            policy_review=PolicyReviewSignalOut(
                required=True,
                reason=reason,
                message="Manual policy review is required before continuation.",
            ),
            results=[],
            corpus_version=corpus_version,
            index_version=index_version,
            retrieval_config=request.retrieval_config,
            correlation_id=correlation_id,
            audit_event_id=UUID(event.audit_event_id),
            telemetry=telemetry,
        )

    def _audit(
        self,
        *,
        event_type: str,
        actor_ref: str,
        decision_status: str,
        correlation_id: str,
        now: datetime,
        ingestion_run_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> PolicyAuditEventModel:
        try:
            return self.audit_repository.append(
                event_type=event_type,
                actor_ref=actor_ref,
                source="policy-retrieval-api",
                decision_status=decision_status,
                ingestion_run_id=ingestion_run_id,
                correlation_id=correlation_id,
                metadata=metadata,
                now=now,
            )
        except AuditWriteError as exc:
            self.db.rollback()
            raise PolicyRetrievalAuditError(str(exc)) from exc

    def _rank(
        self,
        rows: list[PolicyRetrievalRow],
        config: PolicyRetrievalConfig,
    ) -> list[_RankedPolicyRow]:
        ranked = [
            _RankedPolicyRow(
                source=row,
                rank=0,
                fused_score=round(
                    row.lexical_score * config.lexical_weight
                    + row.vector_score * config.vector_weight,
                    6,
                ),
            )
            for row in rows
        ]
        sorted_rows = sorted(
            ranked,
            key=lambda row: (
                row.fused_score,
                row.source.lexical_score,
                row.source.vector_score,
                row.source.chunk.document_id,
                row.source.chunk.version,
                row.source.chunk.section,
            ),
            reverse=True,
        )
        return [
            _RankedPolicyRow(source=row.source, rank=index, fused_score=row.fused_score)
            for index, row in enumerate(sorted_rows[: config.top_k], start=1)
        ]

    def _chunk_out(
        self,
        row: _RankedPolicyRow,
        corpus_version: str,
        index_version: str,
        config: PolicyRetrievalConfig,
    ) -> PolicyRetrievedChunkOut:
        chunk = row.source.chunk
        return PolicyRetrievedChunkOut(
            rank=row.rank,
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            lexical_score=row.source.lexical_score,
            vector_score=row.source.vector_score,
            fused_score=row.fused_score,
            reranker_mode=config.reranker_mode,
            citation=PolicyCitationOut(
                document_id=chunk.document_id,
                version=chunk.version,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                chunk_hash=chunk.chunk_hash,
                effective_from=chunk.effective_from,
                effective_to=chunk.effective_to,
                ingestion_run_id=UUID(chunk.ingestion_run_id),
                corpus_version=corpus_version,
                index_version=index_version,
            ),
        )

    def _citation_failure(
        self,
        rows: list[_RankedPolicyRow],
    ) -> PolicyRetrievalAbstentionReason | None:
        for row in rows:
            chunk = row.source.chunk
            if not all(
                [
                    chunk.document_id,
                    chunk.version,
                    chunk.section,
                    chunk.chunk_id,
                    chunk.chunk_hash,
                    chunk.ingestion_run_id,
                ]
            ):
                return PolicyRetrievalAbstentionReason.missing_citation
        return None

    def _is_ambiguous(
        self,
        rows: list[_RankedPolicyRow],
        config: PolicyRetrievalConfig,
    ) -> bool:
        if len(rows) < 2:
            return False
        return rows[0].fused_score - rows[1].fused_score <= config.ambiguity_threshold

    def _telemetry(
        self,
        *,
        request: PolicyRetrievalRequest,
        correlation_id: str,
        corpus_version: str | None,
        index_version: str | None,
        candidate_count: int,
        result_count: int,
        confidence: float,
        abstention_reason: PolicyRetrievalAbstentionReason | None,
        started: float,
    ) -> PolicyRetrievalTelemetryOut:
        return PolicyRetrievalTelemetryOut(
            case_id=request.case_id,
            workflow_id=request.workflow_id,
            correlation_id=correlation_id,
            corpus_version=corpus_version,
            index_version=index_version,
            retrieval_config_version=request.retrieval_config.version,
            eligible_candidate_count=candidate_count,
            returned_result_count=result_count,
            confidence=confidence,
            abstention_reason=abstention_reason,
            latency_ms=max(0, round((perf_counter() - started) * 1000)),
        )

    def _duplicate_card_eval_request(
        self,
        config: PolicyRetrievalConfig,
        actor_ref: str,
    ) -> PolicyRetrievalRequest:
        return PolicyRetrievalRequest(
            query="duplicate card transaction issuer review evidence merchant context",
            effective_date=datetime(2026, 9, 4, tzinfo=UTC),
            product="card",
            channel="web",
            jurisdiction="US",
            actor_ref=actor_ref,
            dispute_metadata={"evaluation_fixture": "duplicate-card-policy-retrieval"},
            retrieval_config=config,
        )

    def _validate_actor(self, actor_ref: str) -> None:
        if not actor_ref:
            raise PolicyAuthorizationError("A policy retrieval actor is required.")

    def _format_vector(self, vector: list[float]) -> str:
        return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"
