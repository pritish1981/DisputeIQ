from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.models import (
    PolicyAuditEventModel,
    PolicyChunkModel,
    PolicyEvaluationResultModel,
    PolicyIngestionRunModel,
)
from app.adapters.repositories import (
    AuditWriteError,
    PolicyAuditRepository,
    PolicyRepository,
    PolicyRunNotFoundError,
    PolicyVersionConflictError,
    utc_now,
)
from app.domain.schemas import (
    PolicyAuditEventOut,
    PolicyDocumentIn,
    PolicyEvaluationOut,
    PolicyIngestionRequest,
    PolicyIngestionRunOut,
    PolicyLineageResponse,
    PolicyPromotionRequest,
    PolicyPromotionResponse,
    PolicySourceType,
    PolicyStatus,
)


class PolicyValidationError(Exception):
    def __init__(self, errors: list[dict[str, object]]) -> None:
        super().__init__("Policy ingestion validation failed")
        self.errors = errors


class PolicyAuthorizationError(Exception):
    pass


@dataclass(frozen=True)
class DeterministicEmbeddingAdapter:
    dimensions: int = 8

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [
            round(int.from_bytes(digest[index : index + 2], "big") / 65535, 6)
            for index in range(0, 16, 2)
        ]


class PolicyIngestionService:
    def __init__(
        self,
        db: Session,
        *,
        repository: PolicyRepository | None = None,
        audit_repository: PolicyAuditRepository | None = None,
        embedding_adapter: DeterministicEmbeddingAdapter | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or PolicyRepository(db)
        self.audit_repository = audit_repository or PolicyAuditRepository(db)
        self.embedding_adapter = embedding_adapter or DeterministicEmbeddingAdapter()

    def ingest(
        self,
        request: PolicyIngestionRequest,
        *,
        correlation_id: str,
    ) -> PolicyIngestionRunOut:
        self._validate_admin_actor(request.actor_ref)
        now = utc_now()
        run = self.repository.create_run(
            actor_ref=request.actor_ref,
            source="policy-admin-api",
            parser_version=request.parser_version,
            chunking_config_hash=request.chunking_config_hash,
            embedding_model=request.embedding_model,
            embedding_config_hash=request.embedding_config_hash,
            retrieval_index_config_hash=request.retrieval_index_config_hash,
            correlation_id=correlation_id,
            now=now,
        )
        validation_errors = self._validate_documents(request.documents)
        try:
            if validation_errors:
                self.repository.complete_run(
                    run,
                    status="failed_validation",
                    validation_errors=validation_errors,
                    telemetry={"documents": len(request.documents), "chunks": 0},
                    now=now,
                )
                self._audit_run(
                    "POLICY_INGESTION_REJECTED",
                    run,
                    request.actor_ref,
                    "rejected",
                    {"validation_errors": validation_errors},
                    now,
                )
                self.db.commit()
                raise PolicyValidationError(validation_errors)

            chunk_count = 0
            for document in request.documents:
                document_model = self.repository.add_document(
                    run=run,
                    document_id=document.document_id,
                    version=document.version,
                    title=document.title,
                    status=document.status.value,
                    approval_ref=document.approval_ref,
                    source_identity=document.source_identity,
                    source_checksum_sha256=document.source_checksum_sha256,
                    effective_from=document.effective_from,
                    effective_to=document.effective_to,
                    product=document.product,
                    channel=document.channel,
                    jurisdiction=document.jurisdiction,
                    source_type=document.source_type.value,
                    content="\n".join(section.text for section in document.sections),
                    now=now,
                )
                chunks = self._chunk_document(document, request)
                for section, content, chunk_id, chunk_hash in chunks:
                    vector = self.embedding_adapter.embed(content)
                    self.repository.add_chunk(
                        document=document_model,
                        run=run,
                        chunk_id=chunk_id,
                        section=section,
                        content=content,
                        chunk_hash=chunk_hash,
                        embedding_vector=self._format_vector(vector),
                        now=now,
                    )
                    chunk_count += 1
                self.audit_repository.append(
                    event_type="POLICY_INGESTION_ACCEPTED",
                    actor_ref=request.actor_ref,
                    source="policy-admin-api",
                    decision_status="accepted",
                    ingestion_run_id=run.run_id,
                    document_id=document.document_id,
                    version=document.version,
                    checksum_sha256=document.source_checksum_sha256,
                    correlation_id=correlation_id,
                    metadata={
                        "status": document.status.value,
                        "source_identity": document.source_identity,
                        "product": document.product,
                        "channel": document.channel,
                        "jurisdiction": document.jurisdiction,
                    },
                    now=now,
                )

            self.repository.complete_run(
                run,
                status="indexed",
                validation_errors=[],
                telemetry={
                    "documents": len(request.documents),
                    "chunks": chunk_count,
                    "vector_index_ready": True,
                    "lexical_index_ready": True,
                },
                now=now,
            )
            self.db.commit()
        except PolicyVersionConflictError:
            self.db.rollback()
            raise
        except AuditWriteError:
            self.db.rollback()
            raise

        return self.get_run(run.run_id)

    def get_run(self, run_id: str | UUID) -> PolicyIngestionRunOut:
        run = self.repository.get_run_detail(str(run_id))
        if run is None:
            raise PolicyRunNotFoundError(f"Policy ingestion run {run_id} was not found")
        audit_events = self.repository.list_audit_events(run.run_id)
        return self._run_out(run, audit_events)

    def promote(
        self,
        request: PolicyPromotionRequest,
        *,
        correlation_id: str,
    ) -> PolicyPromotionResponse:
        self._validate_admin_actor(request.actor_ref)
        now = utc_now()
        run = self.repository.get_run(str(request.ingestion_run_id))
        if run is None:
            raise PolicyRunNotFoundError(
                f"Policy ingestion run {request.ingestion_run_id} was not found"
            )
        metrics, failures = self._evaluate_run(run)
        passed = run.status == "indexed" and not failures
        evaluation = self.repository.add_evaluation(
            ingestion_run_id=run.run_id,
            corpus_version=request.corpus_version,
            index_version=request.index_version,
            passed=passed,
            metrics=metrics,
            threshold_failures=failures,
            correlation_id=correlation_id,
            now=now,
        )
        if not passed:
            self.audit_repository.append(
                event_type="POLICY_CORPUS_PROMOTION_DENIED",
                actor_ref=request.actor_ref,
                source="policy-admin-api",
                decision_status="denied",
                ingestion_run_id=run.run_id,
                correlation_id=correlation_id,
                metadata={
                    "corpus_version": request.corpus_version,
                    "index_version": request.index_version,
                    "evaluation_passed": False,
                    "threshold_failures": failures,
                },
                now=now,
            )
            self.db.commit()
            active = self.repository.active_corpus()
            return self._promotion_response(
                request=request,
                evaluation=evaluation,
                promoted=False,
                active_corpus_version=active.corpus_version if active else None,
                correlation_id=correlation_id,
            )

        try:
            self.repository.promote(
                ingestion_run_id=run.run_id,
                corpus_version=request.corpus_version,
                index_version=request.index_version,
                promoted_by=request.actor_ref,
                correlation_id=correlation_id,
                now=now,
            )
            self.audit_repository.append(
                event_type="POLICY_CORPUS_PROMOTED",
                actor_ref=request.actor_ref,
                source="policy-admin-api",
                decision_status="promoted",
                ingestion_run_id=run.run_id,
                correlation_id=correlation_id,
                metadata={
                    "corpus_version": request.corpus_version,
                    "index_version": request.index_version,
                    "evaluation_passed": True,
                    "metrics": metrics,
                },
                now=now,
            )
            self.db.commit()
        except AuditWriteError:
            self.db.rollback()
            raise
        active = self.repository.active_corpus()
        return self._promotion_response(
            request=request,
            evaluation=evaluation,
            promoted=True,
            active_corpus_version=active.corpus_version if active else None,
            correlation_id=correlation_id,
        )

    def lineage(self, chunk_id: str, *, correlation_id: str) -> PolicyLineageResponse:
        chunk = self.repository.get_chunk(chunk_id)
        if chunk is None:
            raise PolicyRunNotFoundError(f"Policy chunk {chunk_id} was not found")
        active = self.repository.active_corpus()
        corpus_version = None
        index_version = None
        if active is not None and active.ingestion_run_id == chunk.ingestion_run_id:
            corpus_version = active.corpus_version
            index_version = active.index_version
        return PolicyLineageResponse(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            version=chunk.version,
            section=chunk.section,
            effective_from=chunk.effective_from,
            effective_to=chunk.effective_to,
            ingestion_run_id=UUID(chunk.ingestion_run_id),
            source_checksum_sha256=chunk.source_checksum_sha256,
            chunk_hash=chunk.chunk_hash,
            corpus_version=corpus_version,
            index_version=index_version,
            correlation_id=correlation_id,
        )

    def create_reindex_run(
        self,
        request: PolicyIngestionRequest,
        *,
        correlation_id: str,
    ) -> PolicyIngestionRunOut:
        run = self.ingest(request, correlation_id=correlation_id)
        self.audit_repository.append(
            event_type="POLICY_REINDEX_CREATED",
            actor_ref=request.actor_ref,
            source="policy-admin-api",
            decision_status="created",
            ingestion_run_id=str(run.run_id),
            correlation_id=correlation_id,
            metadata={
                "parser_version": request.parser_version,
                "chunking_config_hash": request.chunking_config_hash,
                "embedding_model": request.embedding_model,
                "retrieval_index_config_hash": request.retrieval_index_config_hash,
            },
            now=utc_now(),
        )
        self.db.commit()
        return self.get_run(run.run_id)

    def _validate_documents(self, documents: list[PolicyDocumentIn]) -> list[dict[str, object]]:
        errors: list[dict[str, object]] = []
        for index, document in enumerate(documents):
            prefix = f"documents[{index}]"
            if document.source_type is not PolicySourceType.approved_policy:
                errors.append(
                    {
                        "field": f"{prefix}.source_type",
                        "code": "NON_POLICY_SOURCE",
                        "message": (
                            "Historical case, evidence, notes and examples are "
                            "not production policy corpus inputs."
                        ),
                    }
                )
            if document.status not in {PolicyStatus.approved, PolicyStatus.active}:
                errors.append(
                    {
                        "field": f"{prefix}.status",
                        "code": "UNAPPROVED_OR_INACTIVE",
                        "message": "Only approved or active policy documents can be ingested.",
                    }
                )
            if (
                document.effective_to is not None
                and document.effective_to < document.effective_from
            ):
                errors.append(
                    {
                        "field": f"{prefix}.effective_to",
                        "code": "INVALID_EFFECTIVE_DATES",
                        "message": "effective_to must be after effective_from.",
                    }
                )
        return errors

    def _chunk_document(
        self,
        document: PolicyDocumentIn,
        request: PolicyIngestionRequest,
    ) -> list[tuple[str, str, str, str]]:
        chunks: list[tuple[str, str, str, str]] = []
        for section in document.sections:
            content = section.text.strip()
            identity = "|".join(
                [
                    document.document_id,
                    document.version,
                    section.section,
                    document.source_checksum_sha256,
                    request.parser_version,
                    request.chunking_config_hash,
                    content,
                ]
            )
            chunk_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            chunk_id = (
                f"{document.document_id}:{document.version}:{section.section}:{chunk_hash[:12]}"
            )
            chunks.append((section.section, content, chunk_id, chunk_hash))
        return chunks

    def _evaluate_run(
        self, run: PolicyIngestionRunModel
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        run_detail = self.repository.get_run_detail(run.run_id)
        documents = run_detail.documents if run_detail is not None else []
        chunks: list[PolicyChunkModel] = [
            chunk for document in documents for chunk in document.chunks
        ]
        metrics: dict[str, object] = {
            "retrieval_quality": 1.0 if chunks else 0.0,
            "citation_correctness": 1.0
            if all(chunk.document_id and chunk.version and chunk.section for chunk in chunks)
            else 0.0,
            "metadata_integrity": 1.0
            if all(chunk.product and chunk.channel and chunk.jurisdiction for chunk in chunks)
            else 0.0,
            "stale_policy_exclusion": 1.0
            if all(
                chunk.status in {PolicyStatus.approved.value, PolicyStatus.active.value}
                for chunk in chunks
            )
            else 0.0,
        }
        failures = [
            {"metric": metric, "threshold": 1.0, "actual": actual}
            for metric, actual in metrics.items()
            if actual != 1.0
        ]
        return metrics, failures

    def _run_out(
        self,
        run: PolicyIngestionRunModel,
        audit_events: list[PolicyAuditEventModel],
    ) -> PolicyIngestionRunOut:
        payload = PolicyIngestionRunOut.model_validate(run)
        payload.audit_events = [PolicyAuditEventOut.model_validate(event) for event in audit_events]
        return payload

    def _promotion_response(
        self,
        *,
        request: PolicyPromotionRequest,
        evaluation: PolicyEvaluationResultModel,
        promoted: bool,
        active_corpus_version: str | None,
        correlation_id: str,
    ) -> PolicyPromotionResponse:
        return PolicyPromotionResponse(
            promoted=promoted,
            corpus_version=request.corpus_version,
            index_version=request.index_version,
            ingestion_run_id=request.ingestion_run_id,
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
            active_corpus_version=active_corpus_version,
            correlation_id=correlation_id,
        )

    def _audit_run(
        self,
        event_type: str,
        run: PolicyIngestionRunModel,
        actor_ref: str,
        decision_status: str,
        metadata: dict[str, object],
        now: datetime,
    ) -> None:
        self.audit_repository.append(
            event_type=event_type,
            actor_ref=actor_ref,
            source="policy-admin-api",
            decision_status=decision_status,
            ingestion_run_id=run.run_id,
            correlation_id=run.correlation_id,
            metadata=metadata,
            now=now,
        )

    def _validate_admin_actor(self, actor_ref: str) -> None:
        if not actor_ref:
            raise PolicyAuthorizationError("A policy-admin actor is required.")

    def _format_vector(self, vector: list[float]) -> str:
        return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"
