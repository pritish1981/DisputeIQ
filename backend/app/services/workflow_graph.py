from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, Literal, TypedDict, cast

from langgraph.graph import END, StateGraph

from app.domain.schemas import ClassificationDecision, PolicyRetrievalResponse

GRAPH_VERSION = "duplicate-card-workflow-v1"

WorkflowNodeName = Literal[
    "intake",
    "classification",
    "authoritative_context",
    "evidence_gate",
    "policy_context",
    "controlled_stop",
]


class WorkflowState(TypedDict, total=False):
    control_evaluation_id: str
    schema_version: str
    case_id: str
    workflow_id: str
    graph_version: str
    state_version: int
    correlation_id: str
    current_node: str
    status: str
    interrupt: dict[str, object]
    stage_summaries: dict[str, object]
    side_effect_keys: list[str]
    node_telemetry: list[dict[str, object]]
    errors: list[dict[str, object]]
    case: dict[str, object]
    resume_payload: dict[str, object]


ALLOWED_NODE_OPERATIONS: dict[str, frozenset[str]] = {
    "rules": frozenset({"rules.evaluate"}),
    "confidence": frozenset({"confidence.evaluate"}),
    "intake": frozenset({"case.read"}),
    "classification": frozenset({"classification.model_gateway"}),
    "authoritative_context": frozenset({"provider_context.reference"}),
    "evidence_gate": frozenset({"evidence.evaluate"}),
    "policy_context": frozenset({"policy.retrieve"}),
    "controlled_stop": frozenset({"workflow.stop"}),
}


class WorkflowToolAuthorizationError(Exception):
    def __init__(self, node_name: str, operation: str) -> None:
        super().__init__(f"Node {node_name} cannot execute operation {operation}")
        self.node_name = node_name
        self.operation = operation


def authorize_node_operation(node_name: str, operation: str) -> None:
    allowed = ALLOWED_NODE_OPERATIONS.get(node_name, frozenset())
    if operation not in allowed:
        raise WorkflowToolAuthorizationError(node_name, operation)


def _record_node(
    state: WorkflowState,
    *,
    node_name: str,
    status: str = "completed",
    started: float,
) -> None:
    telemetry = state.setdefault("node_telemetry", [])
    telemetry.append(
        {
            "node_name": node_name,
            "status": status,
            "attempt_count": 1,
            "latency_ms": int((perf_counter() - started) * 1000),
            "case_id": state["case_id"],
            "workflow_id": state["workflow_id"],
            "graph_version": state["graph_version"],
            "state_version": state["state_version"],
            "correlation_id": state["correlation_id"],
        }
    )
    state["current_node"] = node_name


def _stage_summaries(state: WorkflowState) -> dict[str, object]:
    return state.setdefault("stage_summaries", {})


def _side_effects(state: WorkflowState) -> list[str]:
    return state.setdefault("side_effect_keys", [])


def build_workflow_graph(
    *,
    classify_dispute: Callable[[WorkflowState], ClassificationDecision],
    retrieve_policy: Callable[[WorkflowState], PolicyRetrievalResponse],
    control_nodes: dict[str, Callable[[WorkflowState], WorkflowState]] | None = None,
) -> Any:
    graph = StateGraph(WorkflowState)

    def intake(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("intake", "case.read")
        case = state["case"]
        _stage_summaries(state)["intake"] = {
            "case_id": state["case_id"],
            "case_status": case["status"],
            "dispute_type": case["dispute_type"],
            "transaction_ref": case["transaction_ref"],
        }
        _record_node(state, node_name="intake", started=started)
        return state

    def classification(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("classification", "classification.model_gateway")
        expected_key = (
            f"classification:{state['case_id']}:classification-output-v1:classification-router-v1"
        )
        if expected_key in _side_effects(state) and "classification" in _stage_summaries(state):
            cached = _stage_summaries(state)["classification"]
            if (
                control_nodes
                and isinstance(cached, dict)
                and cached.get("category") != ("duplicate_card_transaction")
            ):
                state["status"] = "CONTROLLED_STOP"
                state["interrupt"] = {
                    "required": True,
                    "reason": "category_downstream_out_of_scope",
                    "message": "Deterministic controls are enabled only for duplicate-card cases.",
                    "resume_requirements": ["future_phase_category_workflow"],
                }
            _record_node(state, node_name="classification", started=started)
            return state
        decision = classify_dispute(state)
        telemetry = decision.telemetry.model_dump(mode="json")
        if decision.output is not None:
            output = decision.output.model_dump(mode="json")
            _stage_summaries(state)["classification"] = {
                "category": output["category"],
                "confidence": output["confidence"],
                "supporting_attributes": output["supporting_attributes"],
                "schema_version": output["schema_version"],
                "prompt_version": output["prompt_version"],
                "model_route_version": output["model_route_version"],
                "correlation_id": output["correlation_id"],
                "threshold": decision.threshold,
                "accepted": decision.accepted,
                "telemetry": telemetry,
                "evaluation_metadata": decision.evaluation_metadata,
            }
        else:
            _stage_summaries(state)["classification"] = {
                "category": None,
                "confidence": None,
                "threshold": decision.threshold,
                "accepted": False,
                "reason": decision.reason.value if decision.reason is not None else None,
                "telemetry": telemetry,
                "evaluation_metadata": decision.evaluation_metadata,
            }
        key = (
            f"classification:{state['case_id']}:"
            f"{telemetry['schema_version']}:{telemetry['prompt_version']}"
        )
        if decision.accepted and key not in _side_effects(state):
            _side_effects(state).append(key)
        if decision.manual_classification_required:
            state["status"] = "WAITING_MANUAL_CLASSIFICATION"
            state["interrupt"] = {
                "required": True,
                "reason": "manual_classification",
                "message": "Classification requires authorized manual review before continuation.",
                "resume_requirements": ["authorized_manual_classification"],
            }
        elif (
            decision.output is not None
            and decision.output.category.value != "duplicate_card_transaction"
        ):
            state["status"] = "CONTROLLED_STOP"
            state["interrupt"] = {
                "required": True,
                "reason": "category_downstream_out_of_scope",
                "message": (
                    "Phase 006 classifies this supported category but downstream "
                    "workflow stages are not yet enabled for it."
                ),
                "resume_requirements": ["future_phase_category_workflow"],
            }
        _record_node(state, node_name="classification", started=started)
        return state

    def authoritative_context(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("authoritative_context", "provider_context.reference")
        if control_nodes:
            state = control_nodes["authoritative_context"](state)
            _record_node(state, node_name="authoritative_context", started=started)
            return state
        case = cast(dict[str, Any], state["case"])
        provider_context = cast(list[dict[str, object]], case.get("provider_context", []))
        refs = [
            {
                "provider_context_id": item["provider_context_id"],
                "provider_name": item["provider_name"],
                "record_type": item["record_type"],
                "source_record_ref": item["source_record_ref"],
                "response_hash": item["response_hash"],
            }
            for item in provider_context
        ]
        _stage_summaries(state)["authoritative_context"] = {
            "reference_count": len(refs),
            "references": refs,
        }
        key = f"provider-context-reference:{state['case_id']}"
        if key not in _side_effects(state):
            _side_effects(state).append(key)
        _record_node(state, node_name="authoritative_context", started=started)
        return state

    def evidence_gate(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("evidence_gate", "evidence.evaluate")
        if control_nodes:
            state = control_nodes["evidence_gate"](state)
            _record_node(state, node_name="evidence_gate", started=started)
            return state
        case = cast(dict[str, Any], state["case"])
        evidence_items = cast(list[dict[str, object]], case.get("evidence_metadata", []))
        if not evidence_items:
            state["status"] = "WAITING_EVIDENCE"
            state["interrupt"] = {
                "required": True,
                "reason": "missing_mandatory_evidence",
                "message": "At least one evidence metadata record is required.",
                "resume_requirements": ["register_evidence_metadata", "authorized_resume"],
            }
        _stage_summaries(state)["evidence"] = {
            "required": ["customer_statement_or_receipt"],
            "available_count": len(evidence_items),
            "missing": [] if evidence_items else ["customer_statement_or_receipt"],
            "status": "complete" if evidence_items else "missing",
            "mode": "deterministic-phase-005",
        }
        _record_node(state, node_name="evidence_gate", started=started)
        return state

    def policy_context(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("policy_context", "policy.retrieve")
        if control_nodes:
            state = control_nodes["policy_context"](state)
            _record_node(state, node_name="policy_context", started=started)
            return state
        response = retrieve_policy(state)
        _stage_summaries(state)["policy_context"] = {
            "status": response.status,
            "approved_context": response.approved_context,
            "requires_policy_review": response.requires_policy_review,
            "confidence": response.confidence,
            "corpus_version": response.corpus_version,
            "index_version": response.index_version,
            "result_count": len(response.results),
            "audit_event_id": str(response.audit_event_id),
        }
        key = f"policy-retrieval:{response.audit_event_id}"
        if key not in _side_effects(state):
            _side_effects(state).append(key)
        if response.requires_policy_review:
            state["status"] = "WAITING_POLICY_REVIEW"
            state["interrupt"] = {
                "required": True,
                "reason": response.abstention_reason.value
                if response.abstention_reason is not None
                else "policy_review",
                "message": "Policy context requires authorized review before continuation.",
                "resume_requirements": ["authorized_policy_review", "authorized_resume"],
            }
        _record_node(state, node_name="policy_context", started=started)
        return state

    def controlled_stop(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("controlled_stop", "workflow.stop")
        if control_nodes:
            state = control_nodes["controlled_stop"](state)
            _record_node(state, node_name="controlled_stop", status="paused", started=started)
            return state
        state["status"] = "CONTROLLED_STOP"
        state["interrupt"] = {
            "required": True,
            "reason": "recommendation_human_decision_out_of_scope",
            "message": (
                "Phase 006 stops before recommendation, durable human decision, "
                "communication and financial finalization."
            ),
            "resume_requirements": ["future_phase_recommendation_and_hitl"],
        }
        _stage_summaries(state)["controlled_stop"] = {
            "next_boundary": "recommendation_and_human_decision",
            "financial_outcome_finalized": False,
            "communication_sent": False,
        }
        _record_node(state, node_name="controlled_stop", status="paused", started=started)
        return state

    def after_classification(state: WorkflowState) -> str:
        if state.get("status") in {"WAITING_MANUAL_CLASSIFICATION", "CONTROLLED_STOP"}:
            return END
        return "authoritative_context"

    def after_evidence(state: WorkflowState) -> str:
        if control_nodes:
            return END if str(state.get("status", "")).startswith("WAITING_") else "policy_context"
        return END if state.get("status") == "WAITING_EVIDENCE" else "policy_context"

    def after_policy(state: WorkflowState) -> str:
        if control_nodes:
            return END if str(state.get("status", "")).startswith("WAITING_") else "rules"
        return END if state.get("status") == "WAITING_POLICY_REVIEW" else "controlled_stop"

    def rules(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("rules", "rules.evaluate")
        assert control_nodes is not None
        state = control_nodes["rules"](state)
        _record_node(state, node_name="rules", started=started)
        return state

    def confidence(state: WorkflowState) -> WorkflowState:
        started = perf_counter()
        authorize_node_operation("confidence", "confidence.evaluate")
        assert control_nodes is not None
        state = control_nodes["confidence"](state)
        _record_node(state, node_name="confidence", started=started)
        return state

    graph.add_node("intake", intake)
    graph.add_node("classification", classification)
    graph.add_node("authoritative_context", authoritative_context)
    graph.add_node("evidence_gate", evidence_gate)
    graph.add_node("policy_context", policy_context)
    graph.add_node("controlled_stop", controlled_stop)
    graph.set_entry_point("intake")
    graph.add_edge("intake", "classification")
    graph.add_conditional_edges("classification", after_classification)
    if control_nodes:
        graph.add_conditional_edges(
            "authoritative_context",
            lambda state: (
                END if str(state.get("status", "")).startswith("WAITING_") else "evidence_gate"
            ),
        )
        graph.add_node("rules", rules)
        graph.add_node("confidence", confidence)
        graph.add_conditional_edges(
            "rules",
            lambda state: (
                END if str(state.get("status", "")).startswith("WAITING_") else "confidence"
            ),
        )
        graph.add_conditional_edges(
            "confidence",
            lambda state: (
                END if str(state.get("status", "")).startswith("WAITING_") else "controlled_stop"
            ),
        )
    else:
        graph.add_edge("authoritative_context", "evidence_gate")
    graph.add_conditional_edges("evidence_gate", after_evidence)
    graph.add_conditional_edges("policy_context", after_policy)
    graph.add_edge("controlled_stop", END)
    return graph.compile()
