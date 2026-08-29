from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_foundation_create_does_not_create_workflow_checkpoint(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/disputes",
        json=valid_payload,
        headers={"Idempotency-Key": "idem-boundary-1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "workflow_run_id" not in body
    assert "checkpoint" not in body


def test_foundation_has_no_ai_or_rag_runtime_imports() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    python_files = [path for path in app_root.rglob("*.py") if path.is_file()]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in python_files)

    forbidden_terms = [
        "langgraph",
        "openai",
        "anthropic",
        "model_gateway",
        "pgvector",
        "embedding",
        "recommendation",
        "communication",
        "human_decision",
    ]
    assert not any(term in combined.lower() for term in forbidden_terms)


def test_openapi_exposes_no_financial_posting_surface(client: TestClient) -> None:
    response = client.get("/openapi.json")
    paths = response.json()["paths"]
    route_text = " ".join(paths.keys()).lower()

    forbidden_terms = ["refund", "credit", "debit", "chargeback", "payment"]
    assert not any(term in route_text for term in forbidden_terms)


def test_durable_foundation_records_are_not_redis_backed() -> None:
    app_root = Path(__file__).resolve().parents[2] / "app"
    python_files = [path for path in app_root.rglob("*.py") if path.is_file()]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in python_files)

    assert "redis" not in combined.lower()
    assert "sqlalchemy" in combined.lower()
