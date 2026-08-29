from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_retrieve_and_replay_dispute(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    headers = {"Idempotency-Key": "idem-api-1", "X-Correlation-ID": "corr-api-1"}

    created = client.post("/api/v1/disputes", json=valid_payload, headers=headers)
    replay = client.post("/api/v1/disputes", json=valid_payload, headers=headers)

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["case_id"] == created.json()["case_id"]
    assert created.headers["x-correlation-id"] == "corr-api-1"

    detail = client.get(f"/api/v1/disputes/{created.json()['case_id']}")
    body = detail.json()

    assert detail.status_code == 200
    assert body["status"] == "Submitted"
    assert body["correlation_id"] == "corr-api-1"
    assert body["timeline"][0]["event_type"] == "CASE_CREATED"
    assert body["audit_events"][0]["event_type"] == "CASE_CREATED"
    assert len(body["provider_context"]) == 3
    assert body["evidence_metadata"][0]["file_name"] == "receipt.png"


def test_missing_required_field_returns_validation_error(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    del valid_payload["transaction_ref"]

    response = client.post(
        "/api/v1/disputes",
        json=valid_payload,
        headers={"Idempotency-Key": "idem-api-2"},
    )

    assert response.status_code == 422
    assert "transaction_ref" in response.text


def test_idempotency_key_reuse_with_different_payload_conflicts(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    headers = {"Idempotency-Key": "idem-api-3"}
    first = client.post("/api/v1/disputes", json=valid_payload, headers=headers)
    changed = dict(valid_payload)
    changed["description"] = "Customer reports a different duplicate card transaction."

    conflict = client.post("/api/v1/disputes", json=changed, headers=headers)

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error_code"] == "IDEMPOTENCY_CONFLICT"


def test_generated_correlation_id_is_returned(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/disputes",
        json=valid_payload,
        headers={"Idempotency-Key": "idem-api-4"},
    )

    assert response.status_code == 201
    assert response.headers["x-correlation-id"].startswith("corr_")
    assert response.json()["correlation_id"] == response.headers["x-correlation-id"]
