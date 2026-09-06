from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings


def test_phase_002_operations_do_not_create_workflow_state(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/cases",
        json=valid_payload,
        headers={"Idempotency-Key": "idem-boundary-1"},
    )

    assert response.status_code == 201
    body = response.json()
    case_id = body["case_id"]
    responses = [
        response,
        client.get(f"/api/v1/cases/{case_id}"),
        client.get("/api/v1/cases"),
        client.get(f"/api/v1/cases/{case_id}/timeline"),
        client.get(f"/api/v1/cases/{case_id}/evidence"),
    ]
    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "evidence_type": "receipt",
            "file_name": "boundary.png",
            "content_type": "image/png",
            "size_bytes": 100,
            "checksum_sha256": "f" * 64,
            "uploader_ref": "customer:cust_1001",
        },
        headers={"Idempotency-Key": "idem-boundary-evidence", "If-Match": "1"},
    )
    responses.append(evidence_response)
    assert all(item.status_code < 300 for item in responses)
    combined = " ".join(item.text.lower() for item in responses)
    assert "workflow_run_id" not in combined
    assert "checkpoint" not in combined


def test_case_api_has_no_ai_or_rag_runtime_imports() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    case_boundary_files = {
        app_root / "api" / "v1" / "cases.py",
        app_root / "api" / "v1" / "disputes.py",
        app_root / "services" / "case_service.py",
        app_root / "adapters" / "synthetic_providers.py",
        app_root / "core" / "correlation.py",
        app_root / "core" / "database.py",
    }
    python_files = [path for path in case_boundary_files if path.is_file()]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in python_files)

    forbidden_terms = [
        "langgraph",
        "openai",
        "anthropic",
        "model_gateway",
        "recommendation",
        "communication",
        "human_decision",
        "hitl",
        "boto3",
        "upload_object",
        "object_storage",
    ]
    assert not any(term in combined.lower() for term in forbidden_terms)
    assert settings.ai_enabled is False
    assert settings.rag_enabled is False


def test_phase_003_policy_ingestion_exposes_no_workflow_or_financial_authority() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    policy_files = [
        app_root / "api" / "v1" / "policies.py",
        app_root / "services" / "policy_ingestion.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in policy_files)

    forbidden_terms = [
        "langgraph",
        "workflow_run",
        "checkpoint",
        "recommendation",
        "communication",
        "human_decision",
        "hitl",
        "refund(",
        "credit(",
        "debit(",
        "chargeback(",
        "settlement_post",
    ]
    assert not any(term in combined.lower() for term in forbidden_terms)


def test_openapi_exposes_no_financial_posting_surface(client: TestClient) -> None:
    response = client.get("/openapi.json")
    paths = response.json()["paths"]
    route_text = " ".join(paths.keys()).lower()

    forbidden_terms = ["refund", "credit", "debit", "chargeback", "payment"]
    assert not any(term in route_text for term in forbidden_terms)


def test_phase_006_workflow_uses_gateway_without_autonomous_financial_surface() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    workflow_files = [
        app_root / "api" / "v1" / "workflows.py",
        app_root / "services" / "workflow_service.py",
        app_root / "services" / "workflow_graph.py",
        app_root / "services" / "classification.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in workflow_files)
    lowered = combined.lower()

    forbidden_terms = [
        "openai",
        "anthropic",
        "recommendation_service",
        "communication_service",
        "send_customer",
        "refund(",
        "credit(",
        "debit(",
        "chargeback(",
        "settlement_post",
    ]
    assert not any(term in lowered for term in forbidden_terms)
    assert "langgraph" in lowered
    assert "modelgateway" in lowered
    assert "financial_outcome_finalized" in lowered


def test_business_capabilities_do_not_import_model_provider_sdks_directly() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    provider_sdk_terms = [
        "from openai",
        "import openai",
        "from anthropic",
        "import anthropic",
        "azure.ai",
        'boto3.client("bedrock',
    ]
    allowed_gateway_files = {
        app_root / "services" / "model_gateway.py",
    }
    inspected_files = [
        path
        for path in app_root.rglob("*.py")
        if path.is_file() and "__pycache__" not in path.parts and path not in allowed_gateway_files
    ]

    violations: list[str] = []
    for path in inspected_files:
        lowered = path.read_text(encoding="utf-8").lower()
        if any(term in lowered for term in provider_sdk_terms):
            violations.append(str(path.relative_to(app_root)))
    assert violations == []


def test_durable_phase_002_records_are_not_redis_backed() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    python_files = [path for path in app_root.rglob("*.py") if path.is_file()]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in python_files)

    assert "redis" not in combined.lower()
    assert "sqlalchemy" in combined.lower()
