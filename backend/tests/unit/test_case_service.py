from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.models import AuditEventModel, EvidenceMetadataModel, TimelineEntryModel
from app.adapters.repositories import (
    AuditRepository,
    AuditWriteError,
    IdempotencyConflictError,
    OptimisticLockError,
)
from app.domain.schemas import CreateCaseRequest, EvidenceMetadataIn
from app.services.case_service import CaseService


def test_case_service_creates_complete_case_aggregate(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    service = CaseService(db_session)
    request = CreateCaseRequest.model_validate(valid_payload)
    response, replayed = service.create_case(request, "idem-1", "corr-test")

    assert replayed is False
    assert response.status == "Submitted"
    assert response.state_version == 1
    assert response.opened_at == response.created_at
    assert response.closed_at is None
    assert response.correlation_id == "corr-test"
    assert len(response.provider_context) == 6
    assert len(response.evidence_metadata) == 1
    assert [event.event_type for event in response.audit_events] == [
        "CASE_CREATED",
        "EVIDENCE_METADATA_REGISTERED",
    ]
    assert [entry.event_type for entry in response.timeline] == [
        "CASE_CREATED",
        "EVIDENCE_METADATA_REGISTERED",
    ]


def test_create_replay_and_conflict_are_side_effect_safe(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    service = CaseService(db_session)
    request = CreateCaseRequest.model_validate(valid_payload)
    first, _ = service.create_case(request, "idem-1", "corr-test")
    second, replayed = service.create_case(request, "idem-1", "corr-other")

    assert replayed is True
    assert second.case_id == first.case_id
    assert service.case_count() == 1

    changed = deepcopy(valid_payload)
    changed["description"] = "Customer reports a different duplicate card transaction."
    with pytest.raises(IdempotencyConflictError):
        service.create_case(CreateCaseRequest.model_validate(changed), "idem-1", "corr-test")

    assert service.case_count() == 1
    assert db_session.scalar(select(func.count()).select_from(AuditEventModel)) == 2
    assert db_session.scalar(select(func.count()).select_from(TimelineEntryModel)) == 2


def test_audit_failure_rolls_back_case_creation(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    service = CaseService(
        db_session,
        audit_repository=AuditRepository(db_session, fail_writes=True),
    )
    request = CreateCaseRequest.model_validate(valid_payload)

    with pytest.raises(AuditWriteError):
        service.create_case(request, "idem-1", "corr-test")

    assert service.case_count() == 0
    assert db_session.scalar(select(func.count()).select_from(AuditEventModel)) == 0


def test_evidence_audit_failure_and_stale_version_leave_state_unchanged(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    payload = deepcopy(valid_payload)
    payload["evidence_metadata"] = []
    normal_service = CaseService(db_session)
    case, _ = normal_service.create_case(
        CreateCaseRequest.model_validate(payload), "idem-create", "corr-create"
    )
    evidence = EvidenceMetadataIn.model_validate(
        {
            "evidence_type": "receipt",
            "file_name": "receipt.png",
            "content_type": "image/png",
            "size_bytes": 100,
            "checksum_sha256": "c" * 64,
            "uploader_ref": "customer:cust_1001",
        }
    )
    failing_service = CaseService(
        db_session,
        audit_repository=AuditRepository(db_session, fail_writes=True),
    )
    with pytest.raises(AuditWriteError):
        failing_service.register_evidence(
            case_id=str(case.case_id),
            request=evidence,
            idempotency_key="idem-evidence-fail",
            expected_version=1,
            correlation_id="corr-evidence",
        )

    persisted = normal_service.get_case(str(case.case_id))
    assert persisted.state_version == 1
    assert persisted.evidence_metadata == []
    assert db_session.scalar(select(func.count()).select_from(EvidenceMetadataModel)) == 0

    successful = normal_service.register_evidence(
        case_id=str(case.case_id),
        request=evidence,
        idempotency_key="idem-evidence-ok",
        expected_version=1,
        correlation_id="corr-evidence",
    )
    assert successful.state_version == 2
    with pytest.raises(OptimisticLockError):
        normal_service.register_evidence(
            case_id=str(case.case_id),
            request=evidence,
            idempotency_key="idem-evidence-stale",
            expected_version=1,
            correlation_id="corr-evidence",
        )
    assert normal_service.get_case(str(case.case_id)).state_version == 2
    assert len(normal_service.list_evidence(str(case.case_id)).items) == 1
