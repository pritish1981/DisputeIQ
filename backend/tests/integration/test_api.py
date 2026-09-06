from __future__ import annotations

from copy import deepcopy
from typing import cast

from fastapi.testclient import TestClient


def create_case(
    client: TestClient,
    payload: dict[str, object],
    key: str = "idem-api-1",
    correlation_id: str = "corr-api-1",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/cases",
        json=payload,
        headers={"Idempotency-Key": key, "X-Correlation-ID": correlation_id},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, object], response.json())


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_retrieve_and_replay_case(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    headers = {"Idempotency-Key": "idem-api-1", "X-Correlation-ID": "corr-api-1"}
    created = client.post("/api/v1/cases", json=valid_payload, headers=headers)
    replay = client.post("/api/v1/cases", json=valid_payload, headers=headers)

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["case_id"] == created.json()["case_id"]
    assert created.headers["x-correlation-id"] == "corr-api-1"

    detail = client.get(f"/api/v1/cases/{created.json()['case_id']}")
    body = detail.json()
    assert detail.status_code == 200
    assert body["status"] == "Submitted"
    assert body["state_version"] == 1
    assert body["opened_at"]
    assert body["closed_at"] is None
    assert body["channel_metadata"] == {}
    assert body["correlation_id"] == "corr-api-1"
    assert body["idempotency_replay_count"] == 1
    assert [item["record_type"] for item in body["provider_context"]] == [
        "account",
        "customer",
        "merchant",
        "refund",
        "settlement",
        "transaction",
    ]
    assert sum(event["event_type"] == "CASE_CREATED" for event in body["audit_events"]) == 1


def test_legacy_dispute_routes_delegate_to_case_service(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    headers = {"Idempotency-Key": "idem-legacy-1"}
    legacy = client.post("/api/v1/disputes", json=valid_payload, headers=headers)
    canonical_replay = client.post("/api/v1/cases", json=valid_payload, headers=headers)

    assert legacy.status_code == canonical_replay.status_code == 201
    assert legacy.json()["case_id"] == canonical_replay.json()["case_id"]
    detail = client.get(f"/api/v1/cases/{legacy.json()['case_id']}")
    assert detail.status_code == 200


def test_create_validation_and_error_contracts(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    missing = deepcopy(valid_payload)
    del missing["transaction_ref"]
    response = client.post(
        "/api/v1/cases",
        json=missing,
        headers={"Idempotency-Key": "idem-validation-1"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_FAILED"
    assert response.json()["correlation_id"].startswith("corr_")
    assert any("transaction_ref" in str(detail["loc"]) for detail in response.json()["details"])

    missing_key = client.post("/api/v1/cases", json=valid_payload)
    assert missing_key.status_code == 422
    assert missing_key.json()["error_code"] == "MISSING_IDEMPOTENCY_KEY"

    unsupported = deepcopy(valid_payload)
    unsupported["dispute_type"] = "not_supported"
    response = client.post(
        "/api/v1/cases",
        json=unsupported,
        headers={"Idempotency-Key": "idem-validation-2"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_FAILED"


def test_idempotency_conflict_has_no_side_effects(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    headers = {"Idempotency-Key": "idem-api-conflict"}
    first = client.post("/api/v1/cases", json=valid_payload, headers=headers)
    changed = deepcopy(valid_payload)
    changed["description"] = "Customer reports a different duplicate card transaction."
    conflict = client.post("/api/v1/cases", json=changed, headers=headers)

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "IDEMPOTENCY_CONFLICT"
    listed = client.get("/api/v1/cases")
    assert listed.json()["total"] == 1
    detail = client.get(f"/api/v1/cases/{first.json()['case_id']}").json()
    assert sum(event["event_type"] == "CASE_CREATED" for event in detail["audit_events"]) == 1


def test_case_listing_search_and_unsupported_filter(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    first = create_case(client, valid_payload, key="idem-list-1")
    second_payload = deepcopy(valid_payload)
    second_payload["channel"] = "analyst"
    second = create_case(client, second_payload, key="idem-list-2", correlation_id="corr-list-2")

    filtered = client.get("/api/v1/cases", params={"channel": "analyst"})
    repeated = client.get("/api/v1/cases")
    repeated_again = client.get("/api/v1/cases")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["case_id"] == second["case_id"]
    assert [item["case_id"] for item in repeated.json()["items"]] == [
        item["case_id"] for item in repeated_again.json()["items"]
    ]
    assert {item["case_id"] for item in repeated.json()["items"]} == {
        first["case_id"],
        second["case_id"],
    }

    unsupported = client.get("/api/v1/cases", params={"customer_ref__contains": "cust"})
    assert unsupported.status_code == 422
    assert unsupported.json()["error_code"] == "UNSUPPORTED_FILTER"


def test_evidence_registration_replay_locking_listing_and_timeline(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    payload = deepcopy(valid_payload)
    payload["evidence_metadata"] = []
    case = create_case(client, payload, key="idem-evidence-case")
    case_id = case["case_id"]
    evidence = {
        "evidence_type": "receipt",
        "file_name": "receipt-2.png",
        "object_ref": "r2://synthetic/receipt-2.png",
        "content_type": "image/png",
        "size_bytes": 2048,
        "checksum_sha256": "b" * 64,
        "source": "customer_upload",
        "uploader_ref": "customer:cust_1001",
    }
    headers = {
        "Idempotency-Key": "idem-evidence-1",
        "If-Match": '"1"',
        "X-Correlation-ID": "corr-evidence-1",
    }
    created = client.post(f"/api/v1/cases/{case_id}/evidence", json=evidence, headers=headers)
    replay = client.post(f"/api/v1/cases/{case_id}/evidence", json=evidence, headers=headers)

    assert created.status_code == replay.status_code == 201
    assert created.json()["state_version"] == 2
    assert replay.json()["replayed"] is True
    assert replay.json()["evidence"]["evidence_id"] == created.json()["evidence"]["evidence_id"]

    stale_headers = {"Idempotency-Key": "idem-evidence-stale", "If-Match": "1"}
    stale = client.post(f"/api/v1/cases/{case_id}/evidence", json=evidence, headers=stale_headers)
    assert stale.status_code == 409
    assert stale.json()["error_code"] == "OPTIMISTIC_LOCK_CONFLICT"

    evidence_list = client.get(f"/api/v1/cases/{case_id}/evidence")
    timeline = client.get(f"/api/v1/cases/{case_id}/timeline")
    detail = client.get(f"/api/v1/cases/{case_id}")
    assert evidence_list.json()["total"] == 1
    assert evidence_list.json()["items"][0]["correlation_id"] == "corr-evidence-1"
    assert [event["event_type"] for event in timeline.json()["items"]] == [
        "CASE_CREATED",
        "EVIDENCE_METADATA_REGISTERED",
    ]
    assert timeline.json()["items"][1]["actor"] == "case-service"
    assert timeline.json()["items"][1]["audit_event_id"]
    assert detail.json()["state_version"] == 2
    assert (
        sum(
            event["event_type"] == "EVIDENCE_METADATA_REGISTERED"
            for event in detail.json()["audit_events"]
        )
        == 1
    )


def test_evidence_validation_unknown_case_and_not_found_contract(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    case = create_case(client, valid_payload, key="idem-errors-case")
    invalid = {
        "file_name": "bad.exe",
        "content_type": "not-a-media-type",
        "size_bytes": 10,
        "checksum_sha256": "bad",
        "uploader_ref": "customer:cust_1001",
    }
    invalid_response = client.post(
        f"/api/v1/cases/{case['case_id']}/evidence",
        json=invalid,
        headers={"Idempotency-Key": "idem-invalid-evidence", "If-Match": "1"},
    )
    assert invalid_response.status_code == 422
    assert invalid_response.json()["error_code"] == "VALIDATION_FAILED"

    unknown = client.get("/api/v1/cases/unknown")
    unknown_evidence = client.get("/api/v1/cases/unknown/evidence")
    unknown_timeline = client.get("/api/v1/cases/unknown/timeline")
    assert unknown.json()["error_code"] == "CASE_NOT_FOUND"
    assert unknown_evidence.json()["error_code"] == "CASE_NOT_FOUND"
    assert unknown_timeline.json()["error_code"] == "CASE_NOT_FOUND"


def test_openapi_publishes_phase_002_contract(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    assert "/api/v1/cases" in paths
    assert "/api/v1/cases/{case_id}" in paths
    assert "/api/v1/cases/{case_id}/evidence" in paths
    assert "/api/v1/cases/{case_id}/timeline" in paths
    assert paths["/api/v1/disputes"]["post"]["deprecated"] is True
