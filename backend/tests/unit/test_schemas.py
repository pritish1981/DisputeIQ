from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    CaseStatus,
    ClassificationInput,
    ClassificationOutput,
    CreateCaseRequest,
    DisputeType,
    ModelGatewayRequest,
    ModelGatewayResponse,
    WorkflowResumeRequest,
    WorkflowStartRequest,
    parse_if_match,
    validate_case_transition,
    validate_workflow_state_payload,
)


def test_create_case_schema_accepts_phase_002_payload(
    valid_payload: dict[str, object],
) -> None:
    request = CreateCaseRequest.model_validate(valid_payload)
    assert request.customer_ref == "cust_1001"
    assert request.transaction_ref == "txn_3001"
    assert request.dispute_type is DisputeType.duplicate_card_transaction


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "short"),
        ("transaction_ref", "bad reference!"),
        ("dispute_type", "not_supported"),
    ],
)
def test_create_case_schema_rejects_invalid_or_unsupported_values(
    valid_payload: dict[str, object],
    field: str,
    value: str,
) -> None:
    payload = deepcopy(valid_payload)
    payload[field] = value
    with pytest.raises(ValidationError):
        CreateCaseRequest.model_validate(payload)


def test_evidence_metadata_validation_rejects_checksum_and_content_type(
    valid_payload: dict[str, object],
) -> None:
    payload = deepcopy(valid_payload)
    evidence = payload["evidence_metadata"]
    assert isinstance(evidence, list)
    evidence[0]["checksum_sha256"] = "bad"
    evidence[0]["content_type"] = "invalid"
    with pytest.raises(ValidationError) as exc_info:
        CreateCaseRequest.model_validate(payload)
    assert "checksum_sha256" in str(exc_info.value)
    assert "content_type" in str(exc_info.value)


def test_phase_002_lifecycle_and_if_match_controls() -> None:
    validate_case_transition(CaseStatus.draft, CaseStatus.submitted)
    with pytest.raises(ValueError):
        validate_case_transition(CaseStatus.submitted, CaseStatus.closed)
    assert parse_if_match('W/"2"') == 2
    with pytest.raises(ValueError):
        parse_if_match("not-a-version")


def test_workflow_start_and_resume_schemas(valid_payload: dict[str, object]) -> None:
    case_id = "11111111-1111-4111-8111-111111111111"
    start = WorkflowStartRequest.model_validate({"case_id": case_id})
    assert str(start.case_id) == case_id
    assert start.graph_version == "duplicate-card-workflow-v1"

    resume = WorkflowResumeRequest.model_validate(
        {"resume_reason": "policy_review_complete", "resume_payload": {"approved": True}}
    )
    assert resume.resume_payload["approved"] is True


def test_workflow_state_payload_rejects_disallowed_or_oversized_fields() -> None:
    validate_workflow_state_payload({"case_id": "case-1", "stage_summaries": {}})
    with pytest.raises(ValueError):
        validate_workflow_state_payload({"provider_payloads": []})
    with pytest.raises(ValueError):
        validate_workflow_state_payload(
            {"stage_summaries": {"classification": {"raw_provider_payload": {}}}}
        )
    with pytest.raises(ValueError):
        validate_workflow_state_payload({"case_id": "case-1", "notes": "x" * 20001})


def test_model_gateway_and_classification_schemas() -> None:
    case_id = "11111111-1111-4111-8111-111111111111"
    request = ModelGatewayRequest.model_validate(
        {
            "capability": "classification",
            "case_id": case_id,
            "correlation_id": "corr-schema",
            "input_text": "Customer reports duplicate card transaction.",
        }
    )
    assert request.route.route_version == "model-route-classification-v1"
    output = ClassificationOutput.model_validate(
        {
            "category": "duplicate_card_transaction",
            "confidence": 0.91,
            "correlation_id": "corr-schema",
        }
    )
    assert output.prompt_version == "classification-router-v1"
    ClassificationInput.model_validate(
        {
            "description": "Failed UPI transfer not credited.",
            "dispute_type_hint": "failed_upi_transfer",
            "correlation_id": "corr-schema",
        }
    )
    response = ModelGatewayResponse.model_validate(
        {
            "status": "accepted",
            "validated_output": output.model_dump(mode="json"),
            "route_version": request.route.route_version,
            "prompt_version": request.prompt.prompt_version,
            "schema_version": request.response_schema_version,
            "telemetry": {
                "capability": "classification",
                "case_id": case_id,
                "workflow_id": None,
                "correlation_id": "corr-schema",
                "provider_route_ref": "deterministic-local",
                "prompt_version": "classification-router-v1",
                "schema_version": "classification-output-v1",
                "latency_ms": 1,
                "token_usage": {"input": 4, "output": 2},
                "attempt_count": 1,
                "fallback_used": False,
                "kill_switch_enabled": False,
                "status": "accepted",
            },
        }
    )
    assert response.validated_output["category"] == "duplicate_card_transaction"


def test_classification_schema_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        ClassificationOutput.model_validate(
            {
                "category": "duplicate_card_transaction",
                "confidence": 2.0,
                "correlation_id": "corr-schema",
            }
        )
