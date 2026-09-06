from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.cases import get_case_service
from app.api.v1.policies import get_policy_retrieval_service, get_policy_service
from app.api.v1.workflows import get_workflow_service
from app.core.config import settings
from app.main import create_app
from app.services.case_service import CaseService
from app.services.classification import ClassificationService
from app.services.model_gateway import DeterministicClassificationProvider, ModelGateway
from app.services.policy_ingestion import PolicyIngestionService
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.workflow_service import WorkflowService


def _create_case(client: TestClient, payload: dict[str, object], key: str = "idem-wf-case") -> Any:
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
    assert body["stage_summaries"]["classification"]["category"] == "duplicate_card_transaction"
    assert body["stage_summaries"]["classification"]["prompt_version"] == "classification-router-v1"
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
    classification_keys = [key for key in side_effect_keys if key.startswith("classification:")]
    assert len(classification_keys) == 1


def test_workflow_api_routes_kill_switch_to_manual_classification(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    app = create_app()

    def workflow_service() -> WorkflowService:
        classification = ClassificationService(
            gateway=ModelGateway(
                provider=DeterministicClassificationProvider(),
                app_settings=settings.__class__(
                    ai_kill_switch_enabled=True,
                    classification_confidence_threshold=0.7,
                ),
            ),
            app_settings=settings.__class__(
                ai_kill_switch_enabled=True,
                classification_confidence_threshold=0.7,
            ),
        )
        return WorkflowService(db_session, classification_service=classification)

    app.dependency_overrides[get_case_service] = lambda: CaseService(db_session)
    app.dependency_overrides[get_policy_service] = lambda: PolicyIngestionService(db_session)
    app.dependency_overrides[get_policy_retrieval_service] = lambda: PolicyRetrievalService(
        db_session
    )
    app.dependency_overrides[get_workflow_service] = workflow_service
    with TestClient(app) as test_client:
        created = _create_case(test_client, valid_payload, "idem-wf-kill-case")
        assert created.status_code == 201
        started = test_client.post(
            "/api/v1/workflows",
            json={"case_id": created.json()["case_id"]},
            headers={"Idempotency-Key": "idem-wf-kill-start"},
        )

    assert started.status_code == 202
    body = started.json()
    assert body["status"] == "WAITING_MANUAL_CLASSIFICATION"
    assert body["interrupt"]["reason"] == "manual_classification"
    assert body["stage_summaries"]["classification"]["reason"] == "ai_kill_switch"
    assert body["stage_summaries"]["classification"]["telemetry"]["kill_switch_enabled"] is True
