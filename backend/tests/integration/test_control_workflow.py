from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.control_repository import ControlRepository
from app.adapters.models import (
    AuditEventModel,
    ControlEvaluationModel,
    ControlReviewRequestModel,
    WorkflowCheckpointModel,
)
from app.adapters.repositories import AuditRepository, WorkflowConflictError
from app.control_fixture_loader import (
    STATEMENT_CHECKSUM,
    load_control_fixtures,
    validate_synthetic_evidence,
)
from app.core.config import Settings
from app.domain.controls import CONTROL_GRAPH_VERSION, ReevaluationRequest
from app.domain.schemas import CreateCaseRequest, WorkflowResumeRequest, WorkflowStartRequest
from app.services.case_service import CaseService
from app.services.classification import ClassificationService
from app.services.workflow_service import WorkflowAuditError, WorkflowService


def make_case(session: Session) -> Any:
    service = CaseService(session)
    return service.create_case(
        CreateCaseRequest.model_validate(
            {
                "customer_ref": "cust_1001",
                "account_ref": "acct_2001",
                "transaction_ref": "txn_3001",
                "channel": "web",
                "description": "Customer reports a duplicate card transaction.",
                "submitted_at": datetime(2026, 9, 8, tzinfo=UTC),
                "evidence_metadata": [
                    {
                        "evidence_type": "customer_statement",
                        "file_name": "statement.txt",
                        "content_type": "text/plain",
                        "size_bytes": 71,
                        "checksum_sha256": STATEMENT_CHECKSUM,
                        "uploader_ref": "test:customer",
                    }
                ],
            }
        ),
        idempotency_key=str(uuid4()),
        correlation_id="controls-test",
    )[0]


def enabled_service(session: Session, **kwargs: Any) -> WorkflowService:
    return WorkflowService(
        session,
        classification_service=ClassificationService(
            app_settings=Settings(ai_enabled=True, ai_kill_switch_enabled=False)
        ),
        **kwargs,
    )


def test_controls_happy_replay_and_scoped_history(db_session: Session) -> None:
    load_control_fixtures(db_session)
    case = make_case(db_session)
    validate_synthetic_evidence(db_session, str(case.case_id))
    db_session.commit()
    service = enabled_service(db_session)
    request = WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION)
    result = service.start_workflow(request, idempotency_key="control-start", correlation_id="ct")
    assert result.interrupt.reason == "deterministic_disposition_ready"
    repository = ControlRepository(db_session)
    history = repository.list(str(result.workflow_id))
    assert len(history) == 1
    detail = history[0]
    assert detail.stages["rules"]["candidate"] == "DUPLICATE_SUPPORTED"
    assert detail.stages["confidence"]["ready"]
    replay = service.start_workflow(request, idempotency_key="control-start", correlation_id="ct2")
    assert replay.replayed
    assert len(repository.list(str(result.workflow_id))) == 1
    for checkpoint in db_session.scalars(
        select(WorkflowCheckpointModel).where(
            WorkflowCheckpointModel.workflow_id == str(result.workflow_id)
        )
    ):
        assert "case" not in checkpoint.state_json
        assert "provider_records" not in str(checkpoint.state_json)
    with pytest.raises(LookupError):
        repository.get(str(uuid4()), detail.evaluation_id)
    with pytest.raises(WorkflowConflictError):
        service.resume_workflow(
            result.workflow_id,
            WorkflowResumeRequest(),
            idempotency_key="bad",
            expected_version=result.state_version,
            correlation_id="ct",
        )


def test_evidence_request_and_linked_resume(db_session: Session) -> None:
    load_control_fixtures(db_session)
    case = make_case(db_session)
    service = enabled_service(db_session)
    result = service.start_workflow(
        WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION),
        idempotency_key="evidence-start",
        correlation_id="ce",
    )
    assert result.status.value == "WAITING_EVIDENCE"
    repository = ControlRepository(db_session)
    prior = repository.list(str(result.workflow_id))[0]
    assert prior.requests[0].status == "OPEN"
    validate_synthetic_evidence(db_session, str(case.case_id))
    db_session.commit()
    resume = WorkflowResumeRequest(
        reevaluation=ReevaluationRequest(
            prior_evaluation_id=prior.evaluation_id,
            reason="validated customer statement",
        )
    )
    resumed = enabled_service(db_session).resume_workflow(
        result.workflow_id,
        resume,
        idempotency_key="resume-evidence",
        expected_version=result.state_version,
        correlation_id="ce-resume",
    )
    assert resumed.interrupt.reason == "deterministic_disposition_ready"
    history = repository.list(str(result.workflow_id))
    assert len(history) == 2
    assert history[0].requests[0].status == "FULFILLED"
    assert history[1].bundle.prior_evaluation_id == prior.evaluation_id
    with pytest.raises(WorkflowConflictError):
        service.resume_workflow(
            result.workflow_id,
            resume,
            idempotency_key="stale",
            expected_version=result.state_version,
            correlation_id="ce",
        )


def test_control_audit_failure_rolls_back(db_session: Session) -> None:
    load_control_fixtures(db_session)
    case = make_case(db_session)
    validate_synthetic_evidence(db_session, str(case.case_id))
    db_session.commit()

    class FailingControlAudit(AuditRepository):
        def append(self, **kwargs: Any) -> AuditEventModel:
            if kwargs["event_type"] == "EVIDENCE_ASSESSED":
                self.fail_writes = True
            return super().append(**kwargs)

    service = enabled_service(db_session, audit_repository=FailingControlAudit(db_session))
    with pytest.raises(WorkflowAuditError):
        service.start_workflow(
            WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION),
            idempotency_key="audit-failure",
            correlation_id="audit-ct",
        )
    assert db_session.scalar(select(func.count()).select_from(ControlEvaluationModel)) == 0
    assert db_session.scalar(select(func.count()).select_from(ControlReviewRequestModel)) == 0
