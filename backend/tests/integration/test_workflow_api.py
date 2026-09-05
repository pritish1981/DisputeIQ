from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _create_case(
    client: TestClient, payload: dict[str, object], key: str = "idem-wf-case"
) -> Any:
    return client.post("/api/v1/cases", json=payload, headers={"Idempotency-Key": key})


def test_start_inspect_and_replay_workflow(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    created = _create_case(client, valid_payload)
    assert created.status_code == 201
    case_id = created.json()["case_id"]

    response = client.post(
        "/api/v1/workflows",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "idem-workflow-start", "X-Correlation-ID": "corr-wf-1"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["case_id"] == case_id
    assert body["workflow_id"]
    assert body["status"] in {"WAITING_POLICY_REVIEW", "CONTROLLED_STOP"}
    assert body["checkpoint"]["checkpoint_seq"] == 2
    assert body["telemetry"]["correlation_id"] == "corr-wf-1"
    assert body["stage_summaries"]["authoritative_context"]["reference_count"] > 0

    detail = client.get(f"/api/v1/workflows/{body['workflow_id']}")
    assert detail.status_code == 200
    assert detail.json()["workflow_id"] == body["workflow_id"]

    replay = client.post(
        "/api/v1/workflows",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "idem-workflow-start"},
    )
    assert replay.status_code == 202
    assert replay.json()["workflow_id"] == body["workflow_id"]
    assert replay.json()["replayed"] is True


def test_workflow_start_conflict_and_not_found(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    missing = client.post(
        "/api/v1/workflows",
        json={"case_id": "11111111-1111-4111-8111-111111111111"},
        headers={"Idempotency-Key": "idem-missing-workflow"},
    )
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "CASE_NOT_FOUND"

    created = _create_case(client, valid_payload, "idem-wf-conflict-case")
    case_id = created.json()["case_id"]
    first = client.post(
        "/api/v1/workflows",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "idem-wf-conflict-start-1"},
    )
    assert first.status_code == 202
    conflict = client.post(
        "/api/v1/workflows",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "idem-wf-conflict-start-2"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "WORKFLOW_CONFLICT"


def test_resume_requires_current_state_version(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    payload = dict(valid_payload)
    payload["evidence_metadata"] = []
    created = _create_case(client, payload, "idem-wf-resume-case")
    case_id = created.json()["case_id"]
    started = client.post(
        "/api/v1/workflows",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "idem-wf-resume-start"},
    )
    assert started.status_code == 202
    workflow_id = started.json()["workflow_id"]
    assert started.json()["status"] == "WAITING_EVIDENCE"

    stale = client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        json={"resume_reason": "evidence_added"},
        headers={"Idempotency-Key": "idem-wf-resume-stale", "If-Match": "1"},
    )
    assert stale.status_code == 409

    current = started.json()["state_version"]
    replayable = client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        json={"resume_reason": "evidence_added"},
        headers={"Idempotency-Key": "idem-wf-resume-current", "If-Match": str(current)},
    )
    assert replayable.status_code == 202
    assert replayable.json()["workflow_id"] == workflow_id
    side_effect_keys = replayable.json()["checkpoint"]["side_effect_keys"]
    assert side_effect_keys.count(f"provider-context-reference:{case_id}") == 1
