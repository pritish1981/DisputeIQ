from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import cast
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.adapters.models import WorkflowCheckpointModel, WorkflowRunModel
from app.adapters.repositories import (
    AuditRepository,
    AuditWriteError,
    CaseRepository,
    IdempotencyConflictError,
    IdempotencyRepository,
    WorkflowConflictError,
    WorkflowRepository,
    WorkflowRunNotFoundError,
    utc_now,
)
from app.domain.schemas import (
    CaseResponse,
    CaseStatus,
    ClassificationDecision,
    ClassificationInput,
    PolicyRetrievalAbstentionReason,
    PolicyRetrievalConfig,
    PolicyRetrievalRequest,
    PolicyRetrievalResponse,
    PolicyRetrievalTelemetryOut,
    PolicyReviewSignalOut,
    WorkflowCheckpointOut,
    WorkflowFailureKind,
    WorkflowInterruptOut,
    WorkflowResponse,
    WorkflowResumeRequest,
    WorkflowStartRequest,
    WorkflowTelemetryOut,
    validate_workflow_state_payload,
)
from app.services.case_service import CaseNotFoundError, CaseService, fingerprint_request
from app.services.classification import ClassificationService
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.workflow_graph import GRAPH_VERSION, WorkflowState, build_workflow_graph

WORKFLOW_START_OPERATION = "workflow-start"
WORKFLOW_RESUME_OPERATION = "workflow-resume"
MAX_WORKFLOW_RETRIES = 3


class WorkflowAuditError(Exception):
    pass


class WorkflowStateValidationError(Exception):
    pass


def classify_workflow_failure(error_code: str, attempt_count: int) -> WorkflowFailureKind:
    validation_markers = ("validation", "invalid", "stale", "conflict")
    fatal_markers = ("audit", "integrity", "unauthorized")
    normalized = error_code.lower()
    if any(marker in normalized for marker in validation_markers):
        return WorkflowFailureKind.validation
    if any(marker in normalized for marker in fatal_markers):
        return WorkflowFailureKind.fatal
    if attempt_count >= MAX_WORKFLOW_RETRIES:
        return WorkflowFailureKind.manual_degradation
    return WorkflowFailureKind.retriable


class WorkflowService:
    def __init__(
        self,
        db: Session,
        *,
        case_service: CaseService | None = None,
        classification_service: ClassificationService | None = None,
        policy_retrieval_service: PolicyRetrievalService | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self.db = db
        self.case_repository = CaseRepository(db)
        self.workflow_repository = WorkflowRepository(db)
        self.idempotency_repository = IdempotencyRepository(db)
        self.case_service = case_service or CaseService(db)
        self.classification_service = classification_service or ClassificationService()
        self.policy_retrieval_service = policy_retrieval_service or PolicyRetrievalService(
            db, auto_commit=False
        )
        self.audit_repository = audit_repository or AuditRepository(db)

    def start_workflow(
        self,
        request: WorkflowStartRequest,
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> WorkflowResponse:
        operation = f"{WORKFLOW_START_OPERATION}:{request.case_id}"
        fingerprint = fingerprint_request(request)
        replay = self._replay(operation, idempotency_key, fingerprint)
        if replay is not None:
            return replay

        case = self.case_service.get_case(str(request.case_id))
        if case.status is not CaseStatus.submitted:
            raise WorkflowConflictError("Only submitted cases can start Phase 005 workflow")

        now = utc_now()
        started = perf_counter()
        try:
            with self.db.begin_nested():
                run = self.workflow_repository.create_run(
                    case_id=str(request.case_id),
                    graph_version=request.graph_version,
                    correlation_id=correlation_id,
                    actor_ref=request.actor_ref,
                    now=now,
                )
                self._append_audit(
                    case_id=run.case_id,
                    workflow_id=run.workflow_id,
                    event_type="WORKFLOW_STARTED",
                    state_version=run.state_version,
                    correlation_id=correlation_id,
                    metadata={
                        "graph_version": run.graph_version,
                        "current_node": run.current_node,
                        "checkpoint_seq": run.checkpoint_seq,
                    },
                    now=now,
                )
                initial_state = self._initial_state(
                    case=case,
                    workflow_id=run.workflow_id,
                    graph_version=request.graph_version,
                    state_version=run.state_version,
                    correlation_id=correlation_id,
                )
                self.workflow_repository.append_checkpoint(
                    run=run,
                    state=dict(initial_state),
                    current_node="start",
                    status="RUNNING",
                    interrupt_reason=None,
                    side_effect_keys=[],
                    telemetry=self._telemetry_dict(
                        case_id=run.case_id,
                        workflow_id=run.workflow_id,
                        graph_version=run.graph_version,
                        current_node="start",
                        state_version=run.state_version,
                        correlation_id=correlation_id,
                        status="RUNNING",
                        node_count=0,
                        checkpoint_count=1,
                        interrupt_count=0,
                        latency_ms=0,
                    ),
                    correlation_id=correlation_id,
                    now=now,
                )
                final_state = self._execute(initial_state)
                final_state["state_version"] = run.state_version
                self._validate_state(dict(final_state))
                status = str(final_state.get("status", "RUNNING"))
                current_node = str(final_state.get("current_node", "unknown"))
                interrupt = final_state.get("interrupt", {})
                interrupt_reason = self._interrupt_reason(interrupt)
                telemetry = self._telemetry_from_state(
                    final_state,
                    status=status,
                    current_node=current_node,
                    checkpoint_count=run.checkpoint_seq + 1,
                    latency_ms=int((perf_counter() - started) * 1000),
                )
                checkpoint = self.workflow_repository.append_checkpoint(
                    run=run,
                    state=dict(final_state),
                    current_node=current_node,
                    status=status,
                    interrupt_reason=interrupt_reason,
                    side_effect_keys=list(final_state.get("side_effect_keys", [])),
                    telemetry=telemetry,
                    correlation_id=correlation_id,
                    now=utc_now(),
                )
                self._append_audit(
                    case_id=run.case_id,
                    workflow_id=run.workflow_id,
                    event_type=self._audit_event_type(status),
                    state_version=run.state_version,
                    correlation_id=correlation_id,
                    metadata={
                        "graph_version": run.graph_version,
                        "current_node": current_node,
                        "checkpoint_seq": checkpoint.checkpoint_seq,
                        "interrupt_reason": interrupt_reason,
                        "side_effect_keys": checkpoint.side_effect_keys,
                        "classification": final_state.get("stage_summaries", {}).get(
                            "classification"
                        ),
                    },
                    now=utc_now(),
                )
                response = self._to_response(run, checkpoint)
                self.idempotency_repository.add(
                    operation,
                    idempotency_key,
                    fingerprint,
                    run.case_id,
                    jsonable_encoder(response),
                    202,
                    correlation_id,
                    now,
                )
            self.db.commit()
        except AuditWriteError as exc:
            self.db.rollback()
            raise WorkflowAuditError("Workflow transition audit recording failed") from exc
        except Exception:
            self.db.rollback()
            raise
        return response

    def get_workflow(self, workflow_id: UUID | str) -> WorkflowResponse:
        run = self.workflow_repository.get_detail(str(workflow_id))
        if run is None:
            raise WorkflowRunNotFoundError(str(workflow_id))
        checkpoint = self.workflow_repository.latest_checkpoint(run.workflow_id)
        return self._to_response(run, checkpoint)

    def resume_workflow(
        self,
        workflow_id: UUID | str,
        request: WorkflowResumeRequest,
        *,
        idempotency_key: str,
        expected_version: int,
        correlation_id: str,
    ) -> WorkflowResponse:
        operation = f"{WORKFLOW_RESUME_OPERATION}:{workflow_id}"
        fingerprint = fingerprint_request(request)
        replay = self._replay(operation, idempotency_key, fingerprint)
        if replay is not None:
            return replay

        now = utc_now()
        started = perf_counter()
        try:
            with self.db.begin_nested():
                run = self.workflow_repository.compare_state_version(
                    str(workflow_id), expected_version
                )
                latest = self.workflow_repository.latest_checkpoint(run.workflow_id)
                if latest is None:
                    raise WorkflowConflictError("Workflow has no durable checkpoint to resume")
                case = self.case_service.get_case(run.case_id)
                state = cast(WorkflowState, dict(latest.state_json))
                state.update(
                    {
                        "case": case.model_dump(mode="json"),
                        "state_version": run.state_version,
                        "correlation_id": correlation_id,
                        "resume_payload": request.resume_payload
                        | {
                            "resume_reason": request.resume_reason,
                            "actor_ref": request.actor_ref,
                        },
                    }
                )
                state["side_effect_keys"] = list(latest.side_effect_keys)
                final_state = self._execute(state)
                final_state["state_version"] = run.state_version
                status = str(final_state.get("status", "RUNNING"))
                current_node = str(final_state.get("current_node", latest.current_node))
                interrupt = final_state.get("interrupt", {})
                interrupt_reason = self._interrupt_reason(interrupt)
                telemetry = self._telemetry_from_state(
                    final_state,
                    status=status,
                    current_node=current_node,
                    checkpoint_count=run.checkpoint_seq + 1,
                    latency_ms=int((perf_counter() - started) * 1000),
                )
                checkpoint = self.workflow_repository.append_checkpoint(
                    run=run,
                    state=dict(final_state),
                    current_node=current_node,
                    status=status,
                    interrupt_reason=interrupt_reason,
                    side_effect_keys=list(final_state.get("side_effect_keys", [])),
                    telemetry=telemetry,
                    correlation_id=correlation_id,
                    now=now,
                )
                self._append_audit(
                    case_id=run.case_id,
                    workflow_id=run.workflow_id,
                    event_type="WORKFLOW_RESUMED",
                    state_version=run.state_version,
                    correlation_id=correlation_id,
                    metadata={
                        "graph_version": run.graph_version,
                        "current_node": current_node,
                        "checkpoint_seq": checkpoint.checkpoint_seq,
                        "interrupt_reason": interrupt_reason,
                        "classification": final_state.get("stage_summaries", {}).get(
                            "classification"
                        ),
                    },
                    now=now,
                )
                response = self._to_response(run, checkpoint)
                self.idempotency_repository.add(
                    operation,
                    idempotency_key,
                    fingerprint,
                    run.case_id,
                    jsonable_encoder(response),
                    202,
                    correlation_id,
                    now,
                )
            self.db.commit()
        except AuditWriteError as exc:
            self.db.rollback()
            raise WorkflowAuditError("Workflow transition audit recording failed") from exc
        except Exception:
            self.db.rollback()
            raise
        return response

    def _replay(
        self, operation: str, idempotency_key: str, fingerprint: str
    ) -> WorkflowResponse | None:
        existing = self.idempotency_repository.get(operation, idempotency_key)
        if existing is None:
            return None
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError("idempotency key reused for different payload")
        self.idempotency_repository.mark_replayed(existing, utc_now())
        self.db.commit()
        if existing.response_json is None:
            raise RuntimeError("completed workflow idempotency record has no response")
        return WorkflowResponse.model_validate(existing.response_json).model_copy(
            update={"replayed": True}
        )

    def _execute(self, state: WorkflowState) -> WorkflowState:
        graph = build_workflow_graph(
            classify_dispute=self._classify_dispute,
            retrieve_policy=self._retrieve_policy,
        )
        result = graph.invoke(state)
        return cast(WorkflowState, result)

    def _classify_dispute(self, state: WorkflowState) -> ClassificationDecision:
        case = state["case"]
        evidence_items = case.get("evidence_metadata", [])
        evidence_count = len(evidence_items) if isinstance(evidence_items, list) else 0
        return self.classification_service.classify(
            ClassificationInput.model_validate(
                {
                    "case_id": UUID(str(state["case_id"])),
                    "workflow_id": UUID(str(state["workflow_id"])),
                    "description": str(case["description"]),
                    "dispute_type_hint": case.get("dispute_type"),
                    "channel": case.get("channel"),
                    "transaction_ref": str(case["transaction_ref"]),
                    "evidence_count": evidence_count,
                    "correlation_id": str(state["correlation_id"]),
                }
            )
        )

    def _retrieve_policy(self, state: WorkflowState) -> PolicyRetrievalResponse:
        if self.policy_retrieval_service.repository.active_corpus() is None:
            return PolicyRetrievalResponse(
                status="abstained",
                approved_context=False,
                requires_policy_review=True,
                confidence=0.0,
                abstention_reason=PolicyRetrievalAbstentionReason.missing_active_corpus,
                policy_review=PolicyReviewSignalOut(
                    required=True,
                    reason=PolicyRetrievalAbstentionReason.missing_active_corpus,
                    message="Manual policy review is required before continuation.",
                ),
                results=[],
                corpus_version=None,
                index_version=None,
                retrieval_config=PolicyRetrievalConfig(),
                correlation_id=str(state["correlation_id"]),
                audit_event_id=UUID(state["workflow_id"]),
                telemetry=PolicyRetrievalTelemetryOut(
                    case_id=UUID(state["case_id"]),
                    workflow_id=UUID(state["workflow_id"]),
                    correlation_id=str(state["correlation_id"]),
                    corpus_version=None,
                    index_version=None,
                    retrieval_config_version="retrieval-config-v1",
                    eligible_candidate_count=0,
                    returned_result_count=0,
                    confidence=0.0,
                    abstention_reason=PolicyRetrievalAbstentionReason.missing_active_corpus,
                    latency_ms=0,
                ),
            )
        case = state["case"]
        submitted_at = CaseResponse.model_validate(case).submitted_at
        request = PolicyRetrievalRequest(
            query=f"duplicate card transaction dispute {case['description']}",
            effective_date=submitted_at.astimezone(UTC),
            product="card",
            channel=str(case["channel"]),
            jurisdiction="US",
            actor_ref="workflow-policy-node",
            case_id=UUID(state["case_id"]),
            workflow_id=UUID(state["workflow_id"]),
        )
        return self.policy_retrieval_service.retrieve(
            request,
            correlation_id=str(state["correlation_id"]),
        )

    def _initial_state(
        self,
        *,
        case: CaseResponse,
        workflow_id: str,
        graph_version: str,
        state_version: int,
        correlation_id: str,
        resume_payload: dict[str, object] | None = None,
    ) -> WorkflowState:
        return WorkflowState(
            {
                "schema_version": "1.0",
                "case_id": str(case.case_id),
                "workflow_id": workflow_id,
                "graph_version": graph_version or GRAPH_VERSION,
                "state_version": state_version,
                "correlation_id": correlation_id,
                "current_node": "start",
                "status": "RUNNING",
                "interrupt": {"required": False},
                "stage_summaries": {},
                "side_effect_keys": [],
                "node_telemetry": [],
                "errors": [],
                "case": case.model_dump(mode="json"),
                "resume_payload": resume_payload or {},
            }
        )

    def _validate_state(self, state: dict[str, object]) -> None:
        try:
            validate_workflow_state_payload(state)
        except ValueError as exc:
            raise WorkflowStateValidationError(str(exc)) from exc

    def _append_audit(
        self,
        *,
        case_id: str,
        workflow_id: str,
        event_type: str,
        state_version: int,
        correlation_id: str,
        metadata: dict[str, object],
        now: datetime,
    ) -> None:
        case = self.case_repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        self.audit_repository.append(
            case=case,
            event_type=event_type,
            object_ref=workflow_id,
            state_version=state_version,
            metadata={"workflow_id": workflow_id, **metadata},
            correlation_id=correlation_id,
            now=now,
        )

    @staticmethod
    def _interrupt_reason(interrupt: object) -> str | None:
        if not isinstance(interrupt, dict) or not interrupt:
            return None
        reason = interrupt.get("reason")
        return str(reason) if reason is not None else None

    def _to_response(
        self,
        run: WorkflowRunModel,
        checkpoint: WorkflowCheckpointModel | None,
    ) -> WorkflowResponse:
        state = checkpoint.state_json if checkpoint is not None else {}
        interrupt = state.get("interrupt", {})
        if not isinstance(interrupt, dict):
            interrupt = {}
        telemetry = run.telemetry if isinstance(run.telemetry, dict) else {}
        checkpoint_out = None
        if checkpoint is not None:
            checkpoint_out = WorkflowCheckpointOut(
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_seq=checkpoint.checkpoint_seq,
                state_version=checkpoint.state_version,
                current_node=checkpoint.current_node,
                status=checkpoint.status,
                state_hash=checkpoint.state_hash,
                interrupt_reason=checkpoint.interrupt_reason,
                side_effect_keys=checkpoint.side_effect_keys,
                telemetry=checkpoint.telemetry,
                correlation_id=checkpoint.correlation_id,
                created_at=checkpoint.created_at,
            )
        return WorkflowResponse(
            workflow_id=run.workflow_id,
            case_id=run.case_id,
            status=run.status,
            current_node=run.current_node,
            state_version=run.state_version,
            graph_version=run.graph_version,
            correlation_id=run.correlation_id,
            checkpoint=checkpoint_out,
            interrupt=WorkflowInterruptOut.model_validate(
                {
                    "required": bool(interrupt.get("required", False)),
                    "reason": interrupt.get("reason"),
                    "message": interrupt.get("message"),
                    "resume_requirements": interrupt.get("resume_requirements", []),
                }
            ),
            stage_summaries=cast(dict[str, object], state.get("stage_summaries", {})),
            error_metadata=cast(list[dict[str, object]], state.get("errors", [])),
            telemetry=WorkflowTelemetryOut.model_validate(telemetry),
        )

    def _telemetry_from_state(
        self,
        state: WorkflowState,
        *,
        status: str,
        current_node: str,
        checkpoint_count: int,
        latency_ms: int,
    ) -> dict[str, object]:
        node_telemetry = list(state.get("node_telemetry", []))
        interrupt = state.get("interrupt", {})
        return self._telemetry_dict(
            case_id=str(state["case_id"]),
            workflow_id=str(state["workflow_id"]),
            graph_version=str(state["graph_version"]),
            current_node=current_node,
            state_version=int(state["state_version"]),
            correlation_id=str(state["correlation_id"]),
            status=status,
            node_count=len(node_telemetry),
            checkpoint_count=checkpoint_count,
            interrupt_count=1 if isinstance(interrupt, dict) and interrupt.get("required") else 0,
            latency_ms=latency_ms,
        ) | {"nodes": node_telemetry}

    @staticmethod
    def _telemetry_dict(
        *,
        case_id: str,
        workflow_id: str,
        graph_version: str,
        current_node: str,
        state_version: int,
        correlation_id: str,
        status: str,
        node_count: int,
        checkpoint_count: int,
        interrupt_count: int,
        latency_ms: int,
    ) -> dict[str, object]:
        return {
            "case_id": case_id,
            "workflow_id": workflow_id,
            "graph_version": graph_version,
            "current_node": current_node,
            "state_version": state_version,
            "correlation_id": correlation_id,
            "node_count": node_count,
            "checkpoint_count": checkpoint_count,
            "interrupt_count": interrupt_count,
            "retry_count": 0,
            "status": status,
            "latency_ms": latency_ms,
        }

    @staticmethod
    def _audit_event_type(status: str) -> str:
        if status.startswith("WAITING_") or status in {"MANUAL_PROCESSING", "CONTROLLED_STOP"}:
            return "WORKFLOW_INTERRUPTED"
        if status == "FAILED":
            return "WORKFLOW_FAILED"
        return "WORKFLOW_CHECKPOINTED"
