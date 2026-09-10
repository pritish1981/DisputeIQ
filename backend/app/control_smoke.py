"""Live PostgreSQL acceptance of the deterministic prefix; creates synthetic audited cases."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.adapters.control_repository import ControlRepository
from app.adapters.models import AuditEventModel, ControlEvaluationModel, WorkflowCheckpointModel
from app.adapters.repositories import WorkflowConflictError
from app.control_fixture_loader import (
    STATEMENT_CHECKSUM,
    SYNTHETIC_STATEMENT,
    load_control_fixtures,
    validate_synthetic_evidence,
)
from app.control_sql_smoke import verify_sql_admission
from app.core.config import Settings
from app.core.database import SessionLocal
from app.domain.controls import CONTROL_GRAPH_VERSION, ReevaluationRequest
from app.domain.schemas import (
    CaseResponse,
    CreateCaseRequest,
    WorkflowResumeRequest,
    WorkflowStartRequest,
)
from app.services.case_service import CaseService
from app.services.classification import ClassificationService
from app.services.workflow_service import WorkflowService


def service(db: Session) -> WorkflowService:
    return WorkflowService(
        db,
        classification_service=ClassificationService(
            app_settings=Settings(ai_enabled=True, ai_kill_switch_enabled=False)
        ),
    )


def create_case(db: Session) -> CaseResponse:
    return CaseService(db).create_case(
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
                        "size_bytes": len(SYNTHETIC_STATEMENT),
                        "checksum_sha256": STATEMENT_CHECKSUM,
                        "uploader_ref": "synthetic:customer",
                    }
                ],
            }
        ),
        idempotency_key=str(uuid4()),
        correlation_id="controls-smoke-case",
    )[0]


def replay(workflow_id: str, prior_id: str, version: int, start_key: str) -> str:
    with SessionLocal() as db:
        current = service(db).get_workflow(workflow_id)
        assert current.state_version == version
        detail = ControlRepository(db).output(ControlRepository(db).get(workflow_id, prior_id))
        assert detail.stages["rules"]["candidate"] == "DUPLICATE_SUPPORTED"
        assert detail.stages["confidence"]["ready"] is True
        audit_count = db.scalar(select(func.count()).select_from(AuditEventModel))
        evaluation_count = db.scalar(select(func.count()).select_from(ControlEvaluationModel))
        repeated = service(db).start_workflow(
            WorkflowStartRequest(
                case_id=detail.bundle.case_id,
                graph_version=CONTROL_GRAPH_VERSION,
            ),
            idempotency_key=start_key,
            correlation_id="restart-idempotent-command",
        )
        assert repeated.replayed
        assert db.scalar(select(func.count()).select_from(AuditEventModel)) == audit_count
        assert (
            db.scalar(select(func.count()).select_from(ControlEvaluationModel)) == evaluation_count
        )
        return "process_restart_replay_passed"


def run() -> dict[str, object]:
    with SessionLocal() as db:
        assert db.get_bind().dialect.name == "postgresql", "Live PostgreSQL required"
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == "20260910_0007b"
        load_control_fixtures(db)
        sql_checks = verify_sql_admission(db)
        case = create_case(db)
        request = WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION)
        start_key = str(uuid4())
        waiting = service(db).start_workflow(
            request, idempotency_key=start_key, correlation_id="controls-smoke-start"
        )
        assert waiting.status.value == "WAITING_EVIDENCE"
        history = ControlRepository(db).list(str(waiting.workflow_id))
        prior_id = history[0].evaluation_id
        assert history[0].requests[0].status == "OPEN"
        validate_synthetic_evidence(db, str(case.case_id))
        db.commit()
    # Fresh sessions emulate worker turnover; two simultaneous writers race on the same version.
    resume = WorkflowResumeRequest(
        reevaluation=ReevaluationRequest(
            prior_evaluation_id=prior_id, reason="Synthetic statement validated"
        )
    )

    def contender(index: int) -> str:
        with SessionLocal() as db:
            try:
                result = service(db).resume_workflow(
                    waiting.workflow_id,
                    resume,
                    idempotency_key=f"{start_key}-{index}",
                    expected_version=waiting.state_version,
                    correlation_id=f"controls-race-{index}",
                )
                assert result.interrupt.reason == "deterministic_disposition_ready"
                return "accepted"
            except WorkflowConflictError:
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(contender, [1, 2]))
    assert sorted(outcomes) == ["accepted", "stale"], outcomes
    with SessionLocal() as db:
        current = service(db).get_workflow(waiting.workflow_id)
        history = ControlRepository(db).list(str(current.workflow_id))
        assert len(history) == 2
        assert history[0].requests[0].status == "FULFILLED"
        detail = history[1]
        assert detail.bundle.prior_evaluation_id == prior_id
        assert detail.bundle.versions == history[0].bundle.versions
        assert detail.stages["rules"]["candidate"] == "DUPLICATE_SUPPORTED"
        assert detail.stages["confidence"]["ready"]
        assert detail.stages["policy"]["citations"]
        assert detail.stages["policy"]["eligibility"]["eligible_chunk_ids"]
        stored = ControlRepository(db).get(str(current.workflow_id), detail.evaluation_id)
        other_case = create_case(db)
        values = {
            column.name: getattr(stored, column.name)
            for column in ControlEvaluationModel.__table__.columns
        }
        for changes in (
            {"evaluation_id": str(uuid4())},  # duplicate workflow/state
            {
                "evaluation_id": str(uuid4()),
                "state_version": 999,
                "case_id": str(other_case.case_id),
            },  # cross-case workflow scope
            {
                "evaluation_id": str(uuid4()),
                "state_version": 999,
                "prior_evaluation_id": str(uuid4()),
            },  # missing prior reference
        ):
            try:
                with db.begin_nested():
                    db.execute(insert(ControlEvaluationModel).values(values | changes))
            except IntegrityError:
                pass
            else:
                raise AssertionError("Control database scope/uniqueness constraint missing")
        replayed = service(db).start_workflow(
            request, idempotency_key=start_key, correlation_id="controls-idempotent-replay"
        )
        assert replayed.replayed and replayed.state_version == waiting.state_version
        assert (
            db.scalar(
                select(func.count())
                .select_from(ControlEvaluationModel)
                .where(ControlEvaluationModel.workflow_id == str(current.workflow_id))
            )
            == 2
        )
        checkpoints = list(
            db.scalars(
                select(WorkflowCheckpointModel).where(
                    WorkflowCheckpointModel.workflow_id == str(current.workflow_id)
                )
            )
        )
        assert all("case" not in checkpoint.state_json for checkpoint in checkpoints)
        try:
            with db.begin_nested():
                db.execute(
                    text(
                        "UPDATE control_evaluations SET actor_ref='changed' WHERE evaluation_id=:id"
                    ),
                    {"id": detail.evaluation_id},
                )
        except DBAPIError:
            pass
        else:
            raise AssertionError("PostgreSQL immutability trigger missing")
        restarted = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.control_smoke",
                "--replay",
                str(current.workflow_id),
                detail.evaluation_id,
                str(current.state_version),
                start_key,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "process_restart_replay_passed" in restarted.stdout
        return {
            "status": "passed",
            "case_id": str(case.case_id),
            "workflow_id": str(current.workflow_id),
            "evaluation_id": detail.evaluation_id,
            "candidate": detail.stages["rules"]["candidate"],
            "confidence": detail.stages["confidence"]["score"],
            "versions": detail.bundle.versions,
            "policy_corpus": detail.stages["policy"]["corpus_version"],
            "concurrent_resume": outcomes,
            "restart_replay": "passed",
            "evidence_reassessment": "passed",
            "immutable_storage": "passed",
            "foreign_key_scope_and_uniqueness": "passed",
            "sql_admission": sql_checks,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", nargs=4)
    args = parser.parse_args()
    if args.replay:
        print(replay(args.replay[0], args.replay[1], int(args.replay[2]), args.replay[3]))
    else:
        print(json.dumps(run(), indent=2))
