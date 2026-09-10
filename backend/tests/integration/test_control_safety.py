from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.control_context import ControlContextAdapter
from app.adapters.control_repository import ControlRepository
from app.adapters.models import (
    CaseModel,
    ControlEvaluationModel,
    PolicyChunkModel,
    PolicyDocumentModel,
    WorkflowCheckpointModel,
)
from app.adapters.repositories import WorkflowConflictError, WorkflowRepository
from app.adapters.synthetic_providers import ProviderRecord, SyntheticBankingProvider
from app.control_fixture_loader import load_control_fixtures, validate_synthetic_evidence
from app.control_smoke import create_case, service
from app.domain.controls import CONTROL_GRAPH_VERSION, EvidenceItem, ReevaluationRequest
from app.domain.schemas import WorkflowResumeRequest, WorkflowStartRequest
from app.services.control_workflow import ControlWorkflow
from app.services.rules_engine import RulesEngine


def start(db: Session, **kwargs: Any) -> Any:
    load_control_fixtures(db)
    case = create_case(db)
    validate_synthetic_evidence(db, str(case.case_id))
    db.commit()
    runner = service(db)
    if kwargs:
        runner.control_context = kwargs["context"]
    return runner.start_workflow(
        WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION),
        idempotency_key=str(uuid4()),
        correlation_id="safety-test",
    )


def reevaluate(db: Session, current: Any, retain: bool = True) -> Any:
    prior = ControlRepository(db).list(str(current.workflow_id))[-1]
    return service(db).resume_workflow(
        current.workflow_id,
        WorkflowResumeRequest(
            reevaluation=ReevaluationRequest(
                prior_evaluation_id=prior.evaluation_id,
                reason="Changed authoritative inputs",
                retain_pins=retain,
            )
        ),
        idempotency_key=str(uuid4()),
        expected_version=current.state_version,
        correlation_id="safety-resume",
    )


@pytest.mark.parametrize("failure", ["missing", "timeout", "lineage", "stale", "same-id"])
def test_provider_failures_stop_downstream(db_session: Session, failure: str) -> None:
    class Provider(SyntheticBankingProvider):
        def get_transaction(self, transaction_ref: str) -> ProviderRecord:
            if transaction_ref == "txn_3002":
                if failure == "missing":
                    raise LookupError("missing")
                if failure == "timeout":
                    raise TimeoutError("timeout")
                if failure == "lineage":
                    return replace(
                        super().get_transaction(transaction_ref), source_record_ref="bad"
                    )
                if failure == "same-id":
                    return super().get_transaction("txn_3001")
            return super().get_transaction(transaction_ref)

    provider = Provider(
        source_as_of=datetime.now(UTC) - timedelta(days=2)
        if failure == "stale"
        else datetime.now(UTC)
    )
    current = start(db_session, context=ControlContextAdapter(provider))
    assert current.status.value in {"WAITING_EVIDENCE", "WAITING_RULE_REVIEW"}
    detail = ControlRepository(db_session).list(str(current.workflow_id))[0]
    assert "confidence" not in detail.stages
    assert detail.requests[0].status == "OPEN"


def test_contextual_conflict_creates_manual_request(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquire = ControlContextAdapter.acquire

    def conflicting(self: ControlContextAdapter, case: dict[str, Any]) -> Any:
        facts, items = acquire(self, case)
        first = next(i for i in items if i.kind == "disputed")
        items.append(
            EvidenceItem.model_validate(
                first.model_dump()
                | {
                    "reference": "conflicting:record",
                    "attributes": {"currency": "EUR"},
                }
            )
        )
        return facts, items

    monkeypatch.setattr(ControlContextAdapter, "acquire", conflicting)
    current = start(db_session)
    detail = ControlRepository(db_session).list(str(current.workflow_id))[0]
    assert current.status.value == "WAITING_RULE_REVIEW"
    assert detail.stages["evidence"]["conflicting"]
    assert "policy" not in detail.stages
    assert detail.requests[0].kind == "MANUAL_REVIEW"


@pytest.mark.parametrize("mutation", ["revoked", "content", "effective", "channel"])
def test_policy_pins_rechecked_without_rewriting_history(
    db_session: Session,
    mutation: str,
) -> None:
    current = start(db_session)
    repository = ControlRepository(db_session)
    original = repository.list(str(current.workflow_id))[0].model_dump(mode="json")
    document = db_session.scalar(
        select(PolicyDocumentModel).where(
            PolicyDocumentModel.document_id == "POL-DUP-CARD-CONTROLS"
        )
    )
    assert document
    if mutation == "revoked":
        document.status = "revoked"
    elif mutation == "effective":
        document.effective_to = datetime(2026, 1, 1, tzinfo=UTC)
    elif mutation == "channel":
        document.channel = "mobile"
    else:
        chunk = db_session.scalar(
            select(PolicyChunkModel).where(
                PolicyChunkModel.policy_document_pk == document.policy_document_pk
            )
        )
        assert chunk
        chunk.content = "Tampered text whose stored hash was not changed"
    db_session.commit()
    resumed = reevaluate(db_session, current)
    assert resumed.status.value == "WAITING_POLICY_REVIEW"
    history = repository.list(str(current.workflow_id))
    assert history[0].model_dump(mode="json") == original
    assert "rules" not in history[-1].stages
    assert history[-1].requests[0].kind == "POLICY_REVIEW"


def test_rule_error_persists_manual_review(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: Any) -> Any:
        raise RuntimeError("private exception data")

    monkeypatch.setattr(RulesEngine, "_evaluate", broken)
    # Registry regression must execute before injecting a runtime failure.
    # start's loader runs the regression, so inject only when workflow rules begin.
    monkeypatch.undo()
    original = ControlWorkflow.rules

    def fail_rules(self: ControlWorkflow, state: Any) -> Any:
        monkeypatch.setattr(RulesEngine, "_evaluate", broken)
        return original(self, state)

    monkeypatch.setattr(ControlWorkflow, "rules", fail_rules)
    current = start(db_session)
    detail = ControlRepository(db_session).list(str(current.workflow_id))[0]
    assert detail.stages["rules"]["candidate"] == "REVIEW_REQUIRED"
    assert detail.requests[0].kind == "MANUAL_REVIEW"
    assert "private exception" not in detail.model_dump_json()
    assert "confidence" not in detail.stages


def test_low_confidence_supervisor_request(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = ControlWorkflow.confidence

    def low_signal(self: ControlWorkflow, state: Any) -> Any:
        # A contract with unmet optional evidence can pass mandatory gates with a low score.
        original_stage = self.repo.stage

        def stage(evaluation_id: str, name: str) -> Any:
            value = original_stage(evaluation_id, name)
            assert value is not None
            return value | {"score": "0.1"} if name == "evidence" else value

        monkeypatch.setattr(self.repo, "stage", stage)
        return original(self, state)

    monkeypatch.setattr(ControlWorkflow, "confidence", low_signal)
    current = start(db_session)
    detail = ControlRepository(db_session).list(str(current.workflow_id))[0]
    assert current.status.value == "WAITING_SUPERVISOR_REVIEW"
    assert not detail.stages["confidence"]["ready"]
    assert detail.requests[0].kind == "SUPERVISOR_REVIEW"


@pytest.mark.parametrize("failure", ["request", "checkpoint"])
def test_persistence_failure_rolls_back_all_controls(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    load_control_fixtures(db_session)
    case = create_case(db_session)
    if failure == "request":

        def fail_wait(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("request write unavailable")

        monkeypatch.setattr(ControlWorkflow, "_wait", fail_wait)
    else:
        original = WorkflowRepository.append_checkpoint

        def fail_checkpoint(self: WorkflowRepository, **kwargs: Any) -> Any:
            if kwargs["current_node"] != "start":
                raise RuntimeError("checkpoint write unavailable")
            return original(self, **kwargs)

        monkeypatch.setattr(WorkflowRepository, "append_checkpoint", fail_checkpoint)
    with pytest.raises(RuntimeError):
        service(db_session).start_workflow(
            WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION),
            idempotency_key=str(uuid4()),
            correlation_id="failed-transaction",
        )
    assert db_session.scalar(select(func.count()).select_from(ControlEvaluationModel)) == 0
    assert db_session.scalar(select(func.count()).select_from(WorkflowCheckpointModel)) == 0


def test_scoped_api_and_forged_resume(client: TestClient, db_session: Session) -> None:
    current = start(db_session)
    detail = ControlRepository(db_session).list(str(current.workflow_id))[0]
    path = f"/api/v1/workflows/{current.workflow_id}/control-evaluations"
    headers = {"X-Control-Reader": "true"}
    assert client.get(path).status_code == 403
    assert (
        client.get(path, headers=headers).json()["items"][0]["evaluation_id"]
        == detail.evaluation_id
    )
    response = client.get(f"{path}/{detail.evaluation_id}", headers=headers)
    assert response.status_code == 200
    assert "provider_records" not in response.text and "customer_ref" not in response.text
    assert client.get(f"{path}/{uuid4()}", headers=headers).status_code == 404
    assert client.get(f"{path}/invalid", headers=headers).status_code == 422
    other = f"/api/v1/workflows/{uuid4()}/control-evaluations/{detail.evaluation_id}"
    assert client.get(other, headers=headers).status_code == 404
    resume_path = f"/api/v1/workflows/{current.workflow_id}/resume"
    request = {
        "reevaluation": {
            "prior_evaluation_id": detail.evaluation_id,
            "reason": "forged approval",
            "approved": True,
        }
    }
    assert (
        client.post(
            resume_path,
            json=request,
            headers=headers
            | {
                "Idempotency-Key": "forged",
                "If-Match": str(current.state_version),
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            resume_path,
            json={},
            headers={
                "Idempotency-Key": "unauthorized",
                "If-Match": str(current.state_version),
            },
        ).status_code
        == 403
    )


def test_unknown_graph_rejected(db_session: Session) -> None:
    case = create_case(db_session)
    with pytest.raises(WorkflowConflictError):
        service(db_session).start_workflow(
            WorkflowStartRequest(case_id=case.case_id, graph_version="unknown-version"),
            idempotency_key=str(uuid4()),
            correlation_id="unknown",
        )


@pytest.mark.parametrize(
    "description",
    [
        "Customer reports a failed UPI transfer.",
        "ATM debited account but no cash dispensed.",
    ],
)
def test_other_categories_cannot_resume_into_card_controls(
    db_session: Session,
    description: str,
) -> None:
    case = create_case(db_session)
    stored = db_session.get(CaseModel, str(case.case_id))
    assert stored
    stored.description = description
    db_session.commit()
    runner = service(db_session)
    current = runner.start_workflow(
        WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION),
        idempotency_key=str(uuid4()),
        correlation_id="other-category",
    )
    assert current.interrupt.reason == "category_downstream_out_of_scope"
    resumed = runner.resume_workflow(
        current.workflow_id,
        WorkflowResumeRequest(),
        idempotency_key=str(uuid4()),
        expected_version=current.state_version,
        correlation_id="other-category-retry",
    )
    assert resumed.interrupt.reason == "category_downstream_out_of_scope"
    assert ControlRepository(db_session).list(str(current.workflow_id)) == []
