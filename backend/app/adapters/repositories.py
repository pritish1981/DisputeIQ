from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Select, String, bindparam, select, text, update
from sqlalchemy.orm import Session, selectinload

from app.adapters.models import (
    AuditEventModel,
    CaseModel,
    EvidenceMetadataModel,
    IdempotencyRecordModel,
    PolicyAuditEventModel,
    PolicyChunkModel,
    PolicyCorpusVersionModel,
    PolicyDocumentModel,
    PolicyEvaluationResultModel,
    PolicyIngestionRunModel,
    ProviderContextModel,
    TimelineEntryModel,
    WorkflowCheckpointModel,
    WorkflowRunModel,
)
from app.adapters.synthetic_providers import ProviderRecord
from app.domain.schemas import (
    CaseStatus,
    CreateCaseRequest,
    EvidenceMetadataIn,
    EvidenceStatus,
)


class IdempotencyConflictError(Exception):
    pass


class OptimisticLockError(Exception):
    pass


class AuditWriteError(Exception):
    pass


class PolicyVersionConflictError(Exception):
    pass


class PolicyRunNotFoundError(Exception):
    pass


class PolicyPromotionError(Exception):
    pass


class WorkflowConflictError(Exception):
    pass


class WorkflowRunNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class PolicyRetrievalRow:
    chunk: PolicyChunkModel
    corpus_version: str
    index_version: str
    lexical_score: float
    vector_score: float


class IdempotencyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, operation: str, key: str) -> IdempotencyRecordModel | None:
        return self.db.scalar(
            select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.operation == operation,
                IdempotencyRecordModel.idempotency_key == key,
            )
        )

    def mark_replayed(self, record: IdempotencyRecordModel, at: datetime) -> None:
        record.replay_count += 1
        record.last_replayed_at = at

    def add(
        self,
        operation: str,
        key: str,
        request_fingerprint: str,
        case_id: str,
        response_json: dict[str, object],
        status_code: int,
        correlation_id: str,
        created_at: datetime,
    ) -> None:
        self.db.add(
            IdempotencyRecordModel(
                operation=operation,
                idempotency_key=key,
                request_fingerprint=request_fingerprint,
                case_id=case_id,
                response_json=response_json,
                status_code=status_code,
                correlation_id=correlation_id,
                created_at=created_at,
            )
        )

    def replay_count_for_case(self, case_id: str) -> int:
        records = self.db.scalars(
            select(IdempotencyRecordModel).where(IdempotencyRecordModel.case_id == case_id)
        ).all()
        return sum(record.replay_count for record in records)


class CaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_case(
        self,
        request: CreateCaseRequest,
        correlation_id: str,
        now: datetime,
    ) -> CaseModel:
        case = CaseModel(
            case_id=str(uuid4()),
            customer_ref=request.customer_ref,
            account_ref=request.account_ref,
            transaction_ref=request.transaction_ref,
            channel=request.channel.value,
            channel_metadata=request.channel_metadata,
            dispute_type=request.dispute_type.value,
            description=request.description,
            status=CaseStatus.submitted.value,
            correlation_id=correlation_id,
            state_version=1,
            submitted_at=request.submitted_at or now,
            opened_at=now,
            closed_at=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(case)
        return case

    def get(self, case_id: str) -> CaseModel | None:
        return self.db.get(CaseModel, case_id)

    def get_detail(self, case_id: str) -> CaseModel | None:
        stmt = (
            select(CaseModel)
            .where(CaseModel.case_id == case_id)
            .options(
                selectinload(CaseModel.timeline),
                selectinload(CaseModel.evidence_metadata),
                selectinload(CaseModel.provider_context),
                selectinload(CaseModel.audit_events),
            )
        )
        return self.db.scalar(stmt)

    def list_cases(
        self,
        *,
        status: str | None = None,
        customer_ref: str | None = None,
        transaction_ref: str | None = None,
        channel: str | None = None,
        opened_from: datetime | None = None,
        opened_to: datetime | None = None,
    ) -> list[CaseModel]:
        stmt: Select[tuple[CaseModel]] = select(CaseModel)
        if status is not None:
            stmt = stmt.where(CaseModel.status == status)
        if customer_ref is not None:
            stmt = stmt.where(CaseModel.customer_ref == customer_ref)
        if transaction_ref is not None:
            stmt = stmt.where(CaseModel.transaction_ref == transaction_ref)
        if channel is not None:
            stmt = stmt.where(CaseModel.channel == channel)
        if opened_from is not None:
            stmt = stmt.where(CaseModel.opened_at >= opened_from)
        if opened_to is not None:
            stmt = stmt.where(CaseModel.opened_at <= opened_to)
        return list(self.db.scalars(stmt.order_by(CaseModel.opened_at.desc(), CaseModel.case_id)))

    def increment_version(self, case_id: str, expected_version: int, now: datetime) -> int:
        result = self.db.execute(
            update(CaseModel)
            .where(CaseModel.case_id == case_id, CaseModel.state_version == expected_version)
            .values(state_version=CaseModel.state_version + 1, updated_at=now)
        )
        if getattr(result, "rowcount", None) != 1:
            raise OptimisticLockError(
                f"Case version does not match expected version {expected_version}"
            )
        return expected_version + 1

    def count(self) -> int:
        return len(self.db.scalars(select(CaseModel)).all())


class EvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        case_id: str,
        evidence: EvidenceMetadataIn,
        correlation_id: str,
        now: datetime,
    ) -> EvidenceMetadataModel:
        model = EvidenceMetadataModel(
            evidence_id=str(uuid4()),
            case_id=case_id,
            evidence_type=evidence.evidence_type.value,
            file_name=evidence.file_name,
            object_ref=evidence.object_ref,
            content_type=evidence.content_type,
            size_bytes=evidence.size_bytes,
            checksum_sha256=evidence.checksum_sha256,
            source=evidence.source,
            status=EvidenceStatus.registered.value,
            uploader_ref=evidence.uploader_ref,
            correlation_id=correlation_id,
            registered_at=now,
        )
        self.db.add(model)
        return model

    def list_for_case(self, case_id: str) -> list[EvidenceMetadataModel]:
        stmt = (
            select(EvidenceMetadataModel)
            .where(EvidenceMetadataModel.case_id == case_id)
            .order_by(EvidenceMetadataModel.registered_at, EvidenceMetadataModel.evidence_id)
        )
        return list(self.db.scalars(stmt))


class ProviderContextRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_results(self, case_id: str, correlation_id: str, results: list[ProviderRecord]) -> None:
        for result in results:
            self.db.add(
                ProviderContextModel(
                    provider_context_id=str(uuid4()),
                    case_id=case_id,
                    provider_name=result.provider_name,
                    source_record_ref=result.source_record_ref,
                    record_type=result.record_type,
                    payload_json=result.facts,
                    response_hash=result.response_hash,
                    response_version=result.source_version,
                    correlation_id=correlation_id,
                    retrieved_at=result.retrieved_at,
                )
            )


class AuditRepository:
    def __init__(self, db: Session, fail_writes: bool = False) -> None:
        self.db = db
        self.fail_writes = fail_writes

    def append(
        self,
        *,
        case: CaseModel,
        event_type: str,
        object_ref: str,
        state_version: int,
        metadata: dict[str, object],
        correlation_id: str,
        now: datetime,
    ) -> AuditEventModel:
        if self.fail_writes:
            raise AuditWriteError("simulated audit write failure")
        event = AuditEventModel(
            audit_event_id=str(uuid4()),
            case_id=case.case_id,
            event_type=event_type,
            actor_type="SERVICE",
            actor_ref="case-service",
            source="case-api",
            object_ref=object_ref,
            before_hash=None,
            after_hash=None,
            state_version=state_version,
            event_metadata=metadata,
            correlation_id=correlation_id,
            created_at=now,
        )
        self.db.add(event)
        return event

    def append_case_created(self, case: CaseModel, now: datetime) -> AuditEventModel:
        return self.append(
            case=case,
            event_type="CASE_CREATED",
            object_ref=case.case_id,
            state_version=case.state_version,
            metadata={
                "status": case.status,
                "dispute_type": case.dispute_type,
                "transaction_ref": case.transaction_ref,
            },
            correlation_id=case.correlation_id,
            now=now,
        )

    def append_evidence_registered(
        self,
        case: CaseModel,
        evidence: EvidenceMetadataModel,
        state_version: int,
        correlation_id: str,
        now: datetime,
    ) -> AuditEventModel:
        return self.append(
            case=case,
            event_type="EVIDENCE_METADATA_REGISTERED",
            object_ref=evidence.evidence_id,
            state_version=state_version,
            metadata={
                "evidence_id": evidence.evidence_id,
                "evidence_type": evidence.evidence_type,
                "checksum_sha256": evidence.checksum_sha256,
            },
            correlation_id=correlation_id,
            now=now,
        )


class TimelineRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        case_id: str,
        event_type: str,
        message: str,
        audit_event: AuditEventModel,
        correlation_id: str,
        now: datetime,
    ) -> TimelineEntryModel:
        entry = TimelineEntryModel(
            timeline_entry_id=str(uuid4()),
            case_id=case_id,
            event_type=event_type,
            message=message,
            actor="case-service",
            source="case-api",
            audit_event_id=audit_event.audit_event_id,
            correlation_id=correlation_id,
            occurred_at=now,
        )
        self.db.add(entry)
        return entry

    def add_case_created(
        self,
        case: CaseModel,
        audit_event: AuditEventModel,
        now: datetime,
    ) -> TimelineEntryModel:
        return self.add(
            case_id=case.case_id,
            event_type="CASE_CREATED",
            message="Synthetic dispute case created.",
            audit_event=audit_event,
            correlation_id=case.correlation_id,
            now=now,
        )

    def list_for_case(self, case_id: str) -> list[TimelineEntryModel]:
        stmt = (
            select(TimelineEntryModel)
            .where(TimelineEntryModel.case_id == case_id)
            .order_by(TimelineEntryModel.occurred_at, TimelineEntryModel.timeline_entry_id)
        )
        items = list(self.db.scalars(stmt))
        return sorted(
            items,
            key=lambda item: (
                item.occurred_at,
                0 if item.event_type == "CASE_CREATED" else 1,
                item.timeline_entry_id,
            ),
        )


class WorkflowRepository:
    ACTIVE_STATUSES = frozenset(
        {
            "RUNNING",
            "WAITING_EVIDENCE",
            "WAITING_POLICY_REVIEW",
            "WAITING_RULE_REVIEW",
            "WAITING_SUPERVISOR_REVIEW",
            "WAITING_MANUAL_CLASSIFICATION",
            "MANUAL_PROCESSING",
            "CONTROLLED_STOP",
        }
    )

    def __init__(self, db: Session) -> None:
        self.db = db

    def active_for_case(self, case_id: str) -> WorkflowRunModel | None:
        return self.db.scalar(
            select(WorkflowRunModel)
            .where(
                WorkflowRunModel.case_id == case_id,
                WorkflowRunModel.status.in_(self.ACTIVE_STATUSES),
            )
            .order_by(WorkflowRunModel.started_at.desc())
        )

    def create_run(
        self,
        *,
        case_id: str,
        graph_version: str,
        correlation_id: str,
        actor_ref: str,
        now: datetime,
    ) -> WorkflowRunModel:
        existing = self.active_for_case(case_id)
        if existing is not None:
            raise WorkflowConflictError(f"Case {case_id} already has an active workflow")
        run = WorkflowRunModel(
            workflow_id=str(uuid4()),
            case_id=case_id,
            graph_version=graph_version,
            status="RUNNING",
            current_node="start",
            state_version=1,
            checkpoint_seq=0,
            interrupt_reason=None,
            telemetry={},
            correlation_id=correlation_id,
            started_by=actor_ref,
            started_at=now,
            updated_at=now,
            completed_at=None,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get(self, workflow_id: str) -> WorkflowRunModel | None:
        return self.db.get(WorkflowRunModel, workflow_id)

    def get_detail(self, workflow_id: str) -> WorkflowRunModel | None:
        stmt = (
            select(WorkflowRunModel)
            .where(WorkflowRunModel.workflow_id == workflow_id)
            .options(selectinload(WorkflowRunModel.checkpoints))
        )
        return self.db.scalar(stmt)

    def latest_checkpoint(self, workflow_id: str) -> WorkflowCheckpointModel | None:
        return self.db.scalar(
            select(WorkflowCheckpointModel)
            .where(WorkflowCheckpointModel.workflow_id == workflow_id)
            .order_by(WorkflowCheckpointModel.checkpoint_seq.desc())
        )

    def append_checkpoint(
        self,
        *,
        run: WorkflowRunModel,
        state: dict[str, object],
        current_node: str,
        status: str,
        interrupt_reason: str | None,
        side_effect_keys: list[str],
        telemetry: dict[str, object],
        correlation_id: str,
        now: datetime,
    ) -> WorkflowCheckpointModel:
        if run.graph_version == "duplicate-card-controls-v1":
            state = {
                key: value for key, value in state.items() if key not in {"case", "resume_payload"}
            }
        next_seq = run.checkpoint_seq + 1
        next_version = run.state_version + 1
        telemetry = {
            **telemetry,
            "state_version": next_version,
            "checkpoint_count": next_seq,
        }
        state_hash = self.hash_state(state)
        checkpoint = WorkflowCheckpointModel(
            checkpoint_id=str(uuid4()),
            workflow_id=run.workflow_id,
            case_id=run.case_id,
            checkpoint_seq=next_seq,
            state_version=next_version,
            current_node=current_node,
            status=status,
            state_json=state,
            state_hash=state_hash,
            interrupt_reason=interrupt_reason,
            side_effect_keys=side_effect_keys,
            telemetry=telemetry,
            correlation_id=correlation_id,
            created_at=now,
        )
        run.status = status
        run.current_node = current_node
        run.state_version = next_version
        run.checkpoint_seq = next_seq
        run.interrupt_reason = interrupt_reason
        run.telemetry = telemetry
        run.updated_at = now
        if status in {"COMPLETED", "CONTROLLED_STOP"}:
            run.completed_at = now
        self.db.add(checkpoint)
        self.db.flush()
        return checkpoint

    def compare_state_version(self, workflow_id: str, expected_version: int) -> WorkflowRunModel:
        run = self.db.scalar(
            select(WorkflowRunModel)
            .where(WorkflowRunModel.workflow_id == workflow_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if run is None:
            raise WorkflowRunNotFoundError(workflow_id)
        if run.state_version != expected_version:
            raise WorkflowConflictError(
                f"Workflow version does not match expected version {expected_version}"
            )
        return run

    @staticmethod
    def hash_state(state: dict[str, object]) -> str:
        payload = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(UTC)


class PolicyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_document(self, document_id: str, version: str) -> PolicyDocumentModel | None:
        return self.db.scalar(
            select(PolicyDocumentModel).where(
                PolicyDocumentModel.document_id == document_id,
                PolicyDocumentModel.version == version,
            )
        )

    def create_run(
        self,
        *,
        actor_ref: str,
        source: str,
        parser_version: str,
        chunking_config_hash: str,
        embedding_model: str,
        embedding_config_hash: str,
        retrieval_index_config_hash: str,
        correlation_id: str,
        now: datetime,
    ) -> PolicyIngestionRunModel:
        run = PolicyIngestionRunModel(
            run_id=str(uuid4()),
            status="running",
            actor_ref=actor_ref,
            source=source,
            parser_version=parser_version,
            chunking_config_hash=chunking_config_hash,
            embedding_model=embedding_model,
            embedding_config_hash=embedding_config_hash,
            retrieval_index_config_hash=retrieval_index_config_hash,
            correlation_id=correlation_id,
            validation_errors=[],
            telemetry={},
            created_at=now,
            completed_at=None,
        )
        self.db.add(run)
        return run

    def add_document(
        self,
        *,
        run: PolicyIngestionRunModel,
        document_id: str,
        version: str,
        title: str,
        status: str,
        approval_ref: str,
        source_identity: str,
        source_checksum_sha256: str,
        effective_from: datetime,
        effective_to: datetime | None,
        product: str,
        channel: str,
        jurisdiction: str,
        source_type: str,
        content: str,
        now: datetime,
    ) -> PolicyDocumentModel:
        existing = self.get_document(document_id, version)
        if existing is not None:
            if existing.source_checksum_sha256 != source_checksum_sha256:
                raise PolicyVersionConflictError(
                    f"Policy {document_id} version {version} already exists "
                    "with a different checksum"
                )
            raise PolicyVersionConflictError(
                f"Policy {document_id} version {version} has already been ingested"
            )
        document = PolicyDocumentModel(
            document_id=document_id,
            version=version,
            title=title,
            status=status,
            approval_ref=approval_ref,
            source_identity=source_identity,
            source_checksum_sha256=source_checksum_sha256,
            effective_from=effective_from,
            effective_to=effective_to,
            product=product,
            channel=channel,
            jurisdiction=jurisdiction,
            source_type=source_type,
            content=content,
            ingestion_run_id=run.run_id,
            correlation_id=run.correlation_id,
            created_at=now,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def add_chunk(
        self,
        *,
        document: PolicyDocumentModel,
        run: PolicyIngestionRunModel,
        chunk_id: str,
        section: str,
        content: str,
        chunk_hash: str,
        embedding_vector: str,
        now: datetime,
    ) -> PolicyChunkModel:
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            self.db.execute(
                text(
                    """
                    INSERT INTO policy_chunks (
                        chunk_id,
                        policy_document_pk,
                        document_id,
                        version,
                        section,
                        status,
                        effective_from,
                        effective_to,
                        product,
                        channel,
                        jurisdiction,
                        content,
                        source_checksum_sha256,
                        chunk_hash,
                        parser_version,
                        chunking_config_hash,
                        embedding_model,
                        embedding_config_hash,
                        embedding_vector,
                        vector_index_ready,
                        lexical_index_ready,
                        ingestion_run_id,
                        correlation_id,
                        created_at
                    )
                    VALUES (
                        :chunk_id,
                        :policy_document_pk,
                        :document_id,
                        :version,
                        :section,
                        :status,
                        :effective_from,
                        :effective_to,
                        :product,
                        :channel,
                        :jurisdiction,
                        :content,
                        :source_checksum_sha256,
                        :chunk_hash,
                        :parser_version,
                        :chunking_config_hash,
                        :embedding_model,
                        :embedding_config_hash,
                        CAST(:embedding_vector AS vector),
                        TRUE,
                        TRUE,
                        :ingestion_run_id,
                        :correlation_id,
                        :created_at
                    )
                    """
                ),
                {
                    "chunk_id": chunk_id,
                    "policy_document_pk": document.policy_document_pk,
                    "document_id": document.document_id,
                    "version": document.version,
                    "section": section,
                    "status": document.status,
                    "effective_from": document.effective_from,
                    "effective_to": document.effective_to,
                    "product": document.product,
                    "channel": document.channel,
                    "jurisdiction": document.jurisdiction,
                    "content": content,
                    "source_checksum_sha256": document.source_checksum_sha256,
                    "chunk_hash": chunk_hash,
                    "parser_version": run.parser_version,
                    "chunking_config_hash": run.chunking_config_hash,
                    "embedding_model": run.embedding_model,
                    "embedding_config_hash": run.embedding_config_hash,
                    "embedding_vector": embedding_vector,
                    "ingestion_run_id": run.run_id,
                    "correlation_id": run.correlation_id,
                    "created_at": now,
                },
            )
            inserted = self.get_chunk(chunk_id)
            if inserted is None:
                raise PolicyRunNotFoundError(f"Policy chunk {chunk_id} was not created")
            return inserted
        chunk = PolicyChunkModel(
            chunk_id=chunk_id,
            policy_document_pk=document.policy_document_pk,
            document_id=document.document_id,
            version=document.version,
            section=section,
            status=document.status,
            effective_from=document.effective_from,
            effective_to=document.effective_to,
            product=document.product,
            channel=document.channel,
            jurisdiction=document.jurisdiction,
            content=content,
            source_checksum_sha256=document.source_checksum_sha256,
            chunk_hash=chunk_hash,
            parser_version=run.parser_version,
            chunking_config_hash=run.chunking_config_hash,
            embedding_model=run.embedding_model,
            embedding_config_hash=run.embedding_config_hash,
            embedding_vector=embedding_vector,
            vector_index_ready=True,
            lexical_index_ready=True,
            ingestion_run_id=run.run_id,
            correlation_id=run.correlation_id,
            created_at=now,
        )
        self.db.add(chunk)
        return chunk

    def complete_run(
        self,
        run: PolicyIngestionRunModel,
        *,
        status: str,
        validation_errors: list[dict[str, object]],
        telemetry: dict[str, object],
        now: datetime,
    ) -> None:
        run.status = status
        run.validation_errors = validation_errors
        run.telemetry = telemetry
        run.completed_at = now

    def get_run_detail(self, run_id: str) -> PolicyIngestionRunModel | None:
        stmt = (
            select(PolicyIngestionRunModel)
            .where(PolicyIngestionRunModel.run_id == run_id)
            .options(
                selectinload(PolicyIngestionRunModel.documents).selectinload(
                    PolicyDocumentModel.chunks
                )
            )
        )
        return self.db.scalar(stmt)

    def get_run(self, run_id: str) -> PolicyIngestionRunModel | None:
        return self.db.get(PolicyIngestionRunModel, run_id)

    def list_audit_events(self, run_id: str) -> list[PolicyAuditEventModel]:
        stmt = (
            select(PolicyAuditEventModel)
            .where(PolicyAuditEventModel.ingestion_run_id == run_id)
            .order_by(PolicyAuditEventModel.created_at, PolicyAuditEventModel.audit_event_id)
        )
        return list(self.db.scalars(stmt))

    def get_chunk(self, chunk_id: str) -> PolicyChunkModel | None:
        return self.db.scalar(select(PolicyChunkModel).where(PolicyChunkModel.chunk_id == chunk_id))

    def active_corpus(self) -> PolicyCorpusVersionModel | None:
        return self.db.scalar(
            select(PolicyCorpusVersionModel).where(PolicyCorpusVersionModel.is_active.is_(True))
        )

    def eligible_chunks(
        self,
        *,
        corpus: PolicyCorpusVersionModel,
        effective_date: datetime,
        product: str,
        channel: str,
        jurisdiction: str,
    ) -> list[PolicyChunkModel]:
        stmt = (
            select(PolicyChunkModel)
            .where(
                PolicyChunkModel.ingestion_run_id == corpus.ingestion_run_id,
                PolicyChunkModel.status.in_(("approved", "active")),
                PolicyChunkModel.vector_index_ready.is_(True),
                PolicyChunkModel.lexical_index_ready.is_(True),
                PolicyChunkModel.effective_from <= effective_date,
                (
                    PolicyChunkModel.effective_to.is_(None)
                    | (PolicyChunkModel.effective_to >= effective_date)
                ),
                PolicyChunkModel.product == product,
                PolicyChunkModel.channel == channel,
                PolicyChunkModel.jurisdiction == jurisdiction,
            )
            .order_by(
                PolicyChunkModel.document_id,
                PolicyChunkModel.version,
                PolicyChunkModel.section,
            )
        )
        return list(self.db.scalars(stmt))

    def hybrid_retrieve(
        self,
        *,
        corpus: PolicyCorpusVersionModel,
        query: str,
        query_embedding: str,
        effective_date: datetime,
        product: str,
        channel: str,
        jurisdiction: str,
        limit: int,
        eligible_chunk_ids: list[str] | None = None,
    ) -> list[PolicyRetrievalRow]:
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            return self._postgres_hybrid_retrieve(
                corpus=corpus,
                query=query,
                query_embedding=query_embedding,
                effective_date=effective_date,
                product=product,
                channel=channel,
                jurisdiction=jurisdiction,
                limit=limit,
                eligible_chunk_ids=eligible_chunk_ids,
            )
        return self._sqlite_hybrid_retrieve(
            corpus=corpus,
            query=query,
            query_embedding=query_embedding,
            effective_date=effective_date,
            product=product,
            channel=channel,
            jurisdiction=jurisdiction,
            limit=limit,
            eligible_chunk_ids=eligible_chunk_ids,
        )

    def _postgres_hybrid_retrieve(
        self,
        *,
        corpus: PolicyCorpusVersionModel,
        query: str,
        query_embedding: str,
        effective_date: datetime,
        product: str,
        channel: str,
        jurisdiction: str,
        limit: int,
        eligible_chunk_ids: list[str] | None = None,
    ) -> list[PolicyRetrievalRow]:
        stmt = text(
            """
            SELECT
                c.policy_chunk_pk,
                LEAST(
                    1.0,
                    ts_rank_cd(
                        c.search_tsvector,
                        websearch_to_tsquery('english', :query)
                    ) * 10.0
                ) AS lexical_score,
                GREATEST(
                    0.0,
                    1.0 - (c.embedding_vector <=> CAST(:query_embedding AS vector))
                ) AS vector_score
            FROM policy_chunks c
            WHERE c.ingestion_run_id = :ingestion_run_id
              AND c.status IN ('approved', 'active')
              AND c.vector_index_ready IS TRUE
              AND c.lexical_index_ready IS TRUE
              AND c.effective_from <= :effective_date
              AND (c.effective_to IS NULL OR c.effective_to >= :effective_date)
              AND c.product = :product
              AND c.channel = :channel
              AND c.jurisdiction = :jurisdiction
              AND c.chunk_id IN :eligible_chunk_ids
            ORDER BY lexical_score DESC, vector_score DESC, c.document_id, c.version, c.section
            LIMIT :limit
            """
        )
        stmt = stmt.bindparams(bindparam("eligible_chunk_ids", expanding=True, type_=String))
        if eligible_chunk_ids is None:
            eligible_chunk_ids = [
                c.chunk_id
                for c in self.eligible_chunks(
                    corpus=corpus,
                    effective_date=effective_date,
                    product=product,
                    channel=channel,
                    jurisdiction=jurisdiction,
                )
            ]
        rows = self.db.execute(
            stmt,
            {
                "query": query,
                "query_embedding": query_embedding,
                "ingestion_run_id": corpus.ingestion_run_id,
                "effective_date": effective_date,
                "product": product,
                "channel": channel,
                "jurisdiction": jurisdiction,
                "limit": limit,
                "eligible_chunk_ids": eligible_chunk_ids,
            },
        ).mappings()
        results: list[PolicyRetrievalRow] = []
        for row in rows:
            chunk = self.db.get(PolicyChunkModel, row["policy_chunk_pk"])
            if chunk is None:
                continue
            results.append(
                PolicyRetrievalRow(
                    chunk=chunk,
                    corpus_version=corpus.corpus_version,
                    index_version=corpus.index_version,
                    lexical_score=float(row["lexical_score"] or 0.0),
                    vector_score=float(row["vector_score"] or 0.0),
                )
            )
        return results

    def _sqlite_hybrid_retrieve(
        self,
        *,
        corpus: PolicyCorpusVersionModel,
        query: str,
        query_embedding: str,
        effective_date: datetime,
        product: str,
        channel: str,
        jurisdiction: str,
        limit: int,
        eligible_chunk_ids: list[str] | None = None,
    ) -> list[PolicyRetrievalRow]:
        query_terms = _terms(query)
        query_vector = _parse_vector(query_embedding)
        rows: list[PolicyRetrievalRow] = []
        for chunk in self.eligible_chunks(
            corpus=corpus,
            effective_date=effective_date,
            product=product,
            channel=channel,
            jurisdiction=jurisdiction,
        ):
            if eligible_chunk_ids is not None and chunk.chunk_id not in eligible_chunk_ids:
                continue
            chunk_terms = _terms(chunk.content)
            lexical_score = (
                len(query_terms & chunk_terms) / len(query_terms) if query_terms else 0.0
            )
            vector_score = _cosine(query_vector, _parse_vector(chunk.embedding_vector))
            rows.append(
                PolicyRetrievalRow(
                    chunk=chunk,
                    corpus_version=corpus.corpus_version,
                    index_version=corpus.index_version,
                    lexical_score=round(lexical_score, 6),
                    vector_score=round(vector_score, 6),
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                row.lexical_score,
                row.vector_score,
                row.chunk.document_id,
                row.chunk.version,
                row.chunk.section,
            ),
            reverse=True,
        )[:limit]

    def add_evaluation(
        self,
        *,
        ingestion_run_id: str,
        corpus_version: str,
        index_version: str,
        passed: bool,
        metrics: dict[str, object],
        threshold_failures: list[dict[str, object]],
        correlation_id: str,
        now: datetime,
    ) -> PolicyEvaluationResultModel:
        evaluation = PolicyEvaluationResultModel(
            evaluation_id=str(uuid4()),
            ingestion_run_id=ingestion_run_id,
            corpus_version=corpus_version,
            index_version=index_version,
            passed=passed,
            metrics=metrics,
            threshold_failures=threshold_failures,
            correlation_id=correlation_id,
            evaluated_at=now,
        )
        self.db.add(evaluation)
        return evaluation

    def promote(
        self,
        *,
        ingestion_run_id: str,
        corpus_version: str,
        index_version: str,
        promoted_by: str,
        correlation_id: str,
        now: datetime,
    ) -> PolicyCorpusVersionModel:
        for active in self.db.scalars(
            select(PolicyCorpusVersionModel).where(PolicyCorpusVersionModel.is_active.is_(True))
        ):
            active.is_active = False
        corpus = PolicyCorpusVersionModel(
            corpus_version_id=str(uuid4()),
            corpus_version=corpus_version,
            ingestion_run_id=ingestion_run_id,
            index_version=index_version,
            is_active=True,
            promoted_by=promoted_by,
            correlation_id=correlation_id,
            promoted_at=now,
        )
        self.db.add(corpus)
        return corpus


class PolicyAuditRepository:
    def __init__(self, db: Session, fail_writes: bool = False) -> None:
        self.db = db
        self.fail_writes = fail_writes

    def append(
        self,
        *,
        event_type: str,
        actor_ref: str,
        source: str,
        decision_status: str,
        correlation_id: str,
        now: datetime,
        ingestion_run_id: str | None = None,
        document_id: str | None = None,
        version: str | None = None,
        checksum_sha256: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> PolicyAuditEventModel:
        if self.fail_writes:
            raise AuditWriteError("simulated policy audit write failure")
        event = PolicyAuditEventModel(
            audit_event_id=str(uuid4()),
            ingestion_run_id=ingestion_run_id,
            document_id=document_id,
            version=version,
            checksum_sha256=checksum_sha256,
            event_type=event_type,
            actor_ref=actor_ref,
            source=source,
            decision_status=decision_status,
            event_metadata=metadata or {},
            correlation_id=correlation_id,
            created_at=now,
        )
        self.db.add(event)
        return event


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


def _parse_vector(value: str) -> list[float]:
    stripped = value.strip().removeprefix("[").removesuffix("]")
    if not stripped:
        return []
    return [float(item) for item in stripped.split(",")]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))
