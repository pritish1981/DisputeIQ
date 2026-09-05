from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from app.domain.schemas import (
    PolicyRetrievalAbstentionReason,
    PolicyRetrievalConfig,
    PolicyRetrievalResponse,
    PolicyRetrievalTelemetryOut,
    PolicyReviewSignalOut,
)
from app.services.workflow_graph import (
    WorkflowToolAuthorizationError,
    authorize_node_operation,
    build_workflow_graph,
)
from app.services.workflow_service import classify_workflow_failure


def _base_state(*, evidence: bool = True) -> dict[str, object]:
    case_id = str(uuid4())
    workflow_id = str(uuid4())
    evidence_items = (
        [
            {
                "evidence_id": str(uuid4()),
                "case_id": case_id,
                "evidence_type": "receipt",
                "file_name": "receipt.png",
                "object_ref": None,
                "content_type": "image/png",
                "size_bytes": 10,
                "checksum_sha256": "a" * 64,
                "source": "customer_upload",
                "status": "registered",
                "uploader_ref": "customer:cust_1001",
                "correlation_id": "corr",
                "registered_at": datetime.now(UTC).isoformat(),
            }
        ]
        if evidence
        else []
    )
    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "workflow_id": workflow_id,
        "graph_version": "duplicate-card-workflow-v1",
        "state_version": 1,
        "correlation_id": "corr",
        "current_node": "start",
        "status": "RUNNING",
        "interrupt": {"required": False},
        "stage_summaries": {},
        "side_effect_keys": [],
        "node_telemetry": [],
        "errors": [],
        "case": {
            "case_id": case_id,
            "customer_ref": "cust_1001",
            "account_ref": "acct_2001",
            "transaction_ref": "txn_3001",
            "channel": "web",
            "channel_metadata": {},
            "dispute_type": "duplicate_card_transaction",
            "description": "Customer reports a duplicate card transaction.",
            "status": "Submitted",
            "correlation_id": "corr",
            "state_version": 1,
            "submitted_at": datetime.now(UTC).isoformat(),
            "opened_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "closed_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "timeline": [],
            "evidence_metadata": evidence_items,
            "provider_context": [
                {
                    "provider_context_id": str(uuid4()),
                    "provider_name": "synthetic-transactions",
                    "source_record_ref": "txn_3001",
                    "record_type": "transaction",
                    "payload_json": {"amount": "42.00"},
                    "response_hash": "b" * 64,
                    "response_version": "v1",
                    "correlation_id": "corr",
                    "retrieved_at": datetime.now(UTC).isoformat(),
                }
            ],
            "audit_events": [],
            "idempotency_replay_count": 0,
        },
        "resume_payload": {},
    }


def _policy_response(state: Any, *, requires_review: bool) -> PolicyRetrievalResponse:
    reason = PolicyRetrievalAbstentionReason.missing_active_corpus if requires_review else None
    return PolicyRetrievalResponse(
        status="abstained" if requires_review else "retrieved",
        approved_context=not requires_review,
        requires_policy_review=requires_review,
        confidence=0.0 if requires_review else 0.8,
        abstention_reason=reason,
        policy_review=PolicyReviewSignalOut(required=requires_review, reason=reason),
        results=[],
        corpus_version=None,
        index_version=None,
        retrieval_config=PolicyRetrievalConfig(),
        correlation_id=str(state["correlation_id"]),
        audit_event_id=uuid4(),
        telemetry=PolicyRetrievalTelemetryOut(
            case_id=uuid4(),
            workflow_id=uuid4(),
            correlation_id=str(state["correlation_id"]),
            corpus_version=None,
            index_version=None,
            retrieval_config_version="retrieval-config-v1",
            eligible_candidate_count=0,
            returned_result_count=0,
            confidence=0.0,
            abstention_reason=reason,
            latency_ms=1,
        ),
    )


def test_graph_interrupts_for_missing_evidence() -> None:
    graph = build_workflow_graph(
        retrieve_policy=lambda state: _policy_response(state, requires_review=False)
    )
    result = graph.invoke(_base_state(evidence=False))
    assert result["status"] == "WAITING_EVIDENCE"
    assert result["interrupt"]["reason"] == "missing_mandatory_evidence"


def test_graph_stops_at_policy_review_or_phase_boundary() -> None:
    review_graph = build_workflow_graph(
        retrieve_policy=lambda state: _policy_response(state, requires_review=True)
    )
    review_result = review_graph.invoke(_base_state())
    assert review_result["status"] == "WAITING_POLICY_REVIEW"

    success_graph = build_workflow_graph(
        retrieve_policy=lambda state: _policy_response(state, requires_review=False)
    )
    success_result = success_graph.invoke(_base_state())
    assert success_result["status"] == "CONTROLLED_STOP"
    controlled_stop = success_result["stage_summaries"]["controlled_stop"]
    assert controlled_stop["financial_outcome_finalized"] is False


def test_node_tool_allow_list_denies_unapproved_operations() -> None:
    authorize_node_operation("policy_context", "policy.retrieve")
    with pytest.raises(WorkflowToolAuthorizationError):
        authorize_node_operation("policy_context", "refund.post")


def test_workflow_error_classification_routes_retry_exhaustion_to_manual_degradation() -> None:
    assert classify_workflow_failure("provider_timeout", 1) == "retriable"
    assert classify_workflow_failure("provider_timeout", 3) == "manual_degradation"
    assert classify_workflow_failure("validation_failed", 1) == "validation"
    assert classify_workflow_failure("audit_append_failed", 1) == "fatal"
