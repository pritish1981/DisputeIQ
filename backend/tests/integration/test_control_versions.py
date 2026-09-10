from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.adapters.control_context import ControlContextAdapter
from app.adapters.control_repository import ControlRepository
from app.adapters.synthetic_providers import SyntheticBankingProvider
from app.control_fixture_loader import control_policy_request, validate_synthetic_evidence
from app.control_regression import load_profile
from app.control_smoke import create_case, service
from app.domain.controls import CONTROL_GRAPH_VERSION, ControlProfile, ReevaluationRequest
from app.domain.schemas import PolicyPromotionRequest, WorkflowResumeRequest, WorkflowStartRequest
from app.services import control_workflow
from app.services.control_registry import ControlRegistry
from app.services.policy_ingestion import PolicyIngestionService


def test_threshold_version_activation_and_explicit_reresolution(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = datetime.now(UTC) + timedelta(days=2)
    data = load_profile().model_dump(mode="json")
    data["effective_to"] = boundary.isoformat()
    old = ControlProfile.model_validate(data)
    ControlRegistry(db_session).register(old, "test:admin")
    data["version"] = "controls-v2"
    data["effective_from"] = (boundary + timedelta(seconds=1)).isoformat()
    data["effective_to"] = None
    data["confidence"]["version"] = "case-confidence-v2"
    data["confidence"]["threshold"] = "0.69"
    new = ControlProfile.model_validate(data)
    ControlRegistry(db_session).register(new, "test:admin")
    db_session.commit()
    policy = PolicyIngestionService(db_session)
    ingested = policy.ingest(control_policy_request(), correlation_id="version-policy")

    def promote(label: str) -> Any:
        return policy.promote(
            PolicyPromotionRequest(
                ingestion_run_id=ingested.run_id,
                actor_ref="test:policy-admin",
                corpus_version=f"corpus-{label}",
                index_version=f"index-{label}",
            ),
            correlation_id=f"promote-{label}",
        )

    promote("old")
    case = create_case(db_session)
    validate_synthetic_evidence(db_session, str(case.case_id))
    db_session.commit()
    current = service(db_session).start_workflow(
        WorkflowStartRequest(case_id=case.case_id, graph_version=CONTROL_GRAPH_VERSION),
        idempotency_key=str(uuid4()),
        correlation_id="version-start",
    )
    repo = ControlRepository(db_session)
    original = repo.list(str(current.workflow_id))[0]
    snapshot = original.model_dump(mode="json")
    promote("new")
    future = boundary + timedelta(seconds=2)

    class FutureClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> FutureClock:
            return cls.fromtimestamp(future.timestamp(), tz=UTC)

    monkeypatch.setattr(control_workflow, "datetime", FutureClock)
    runner = service(db_session)
    runner.control_context = ControlContextAdapter(SyntheticBankingProvider(source_as_of=future))
    retained = runner.resume_workflow(
        current.workflow_id,
        WorkflowResumeRequest(
            reevaluation=ReevaluationRequest(
                prior_evaluation_id=original.evaluation_id,
                reason="Updated source snapshots",
            )
        ),
        idempotency_key=str(uuid4()),
        expected_version=current.state_version,
        correlation_id="retain-pins",
    )
    retained_detail = repo.list(str(current.workflow_id))[-1]
    assert retained_detail.bundle.profile_version == old.version
    assert Decimal(retained_detail.stages["confidence"]["threshold"]) == Decimal("0.70")
    assert retained_detail.stages["policy"]["corpus_version"] == "corpus-old"
    rerun = runner.resume_workflow(
        UUID(str(current.workflow_id)),
        WorkflowResumeRequest(
            reevaluation=ReevaluationRequest(
                prior_evaluation_id=retained_detail.evaluation_id,
                reason="Explicitly adopt new approved control and policy versions",
                retain_pins=False,
            )
        ),
        idempotency_key=str(uuid4()),
        expected_version=retained.state_version,
        correlation_id="new-pins",
    )
    latest = repo.list(str(current.workflow_id))[-1]
    assert rerun.interrupt.reason == "deterministic_disposition_ready"
    assert latest.bundle.profile_version == new.version
    assert Decimal(latest.stages["confidence"]["threshold"]) == Decimal("0.69")
    assert latest.stages["policy"]["corpus_version"] == "corpus-new"
    assert repo.list(str(current.workflow_id))[0].model_dump(mode="json") == snapshot
    assert latest.bundle.prior_evaluation_id == retained_detail.evaluation_id
