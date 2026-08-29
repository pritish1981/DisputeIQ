from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.adapters.repositories import AuditRepository, AuditWriteError, IdempotencyConflictError
from app.domain.schemas import CreateDisputeRequest
from app.services.case_service import CaseService


def test_case_service_creates_case_with_context_audit_and_timeline(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    service = CaseService(db_session)
    request = CreateDisputeRequest.model_validate(valid_payload)

    response, replayed = service.create_case(request, "idem-1", "corr-test")

    assert replayed is False
    assert response.status == "Submitted"
    assert response.correlation_id == "corr-test"
    assert len(response.provider_context) == 3
    assert len(response.evidence_metadata) == 1
    assert [event.event_type for event in response.audit_events] == ["CASE_CREATED"]
    assert [entry.event_type for entry in response.timeline] == ["CASE_CREATED"]


def test_case_service_replays_matching_idempotency_key(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    service = CaseService(db_session)
    request = CreateDisputeRequest.model_validate(valid_payload)

    first, _ = service.create_case(request, "idem-1", "corr-test")
    second, replayed = service.create_case(request, "idem-1", "corr-other")

    assert replayed is True
    assert second.case_id == first.case_id
    assert service.case_count() == 1


def test_case_service_rejects_idempotency_conflict(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    service = CaseService(db_session)
    request = CreateDisputeRequest.model_validate(valid_payload)
    service.create_case(request, "idem-1", "corr-test")

    changed = dict(valid_payload)
    changed["description"] = "Customer reports a different duplicate card transaction."

    with pytest.raises(IdempotencyConflictError):
        service.create_case(CreateDisputeRequest.model_validate(changed), "idem-1", "corr-test")

    assert service.case_count() == 1


def test_audit_failure_blocks_case_creation(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    audit_repository = AuditRepository(db_session, fail_writes=True)
    service = CaseService(db_session, audit_repository=audit_repository)
    request = CreateDisputeRequest.model_validate(valid_payload)

    with pytest.raises(AuditWriteError):
        service.create_case(request, "idem-1", "corr-test")

    db_session.rollback()
    assert service.case_count() == 0
