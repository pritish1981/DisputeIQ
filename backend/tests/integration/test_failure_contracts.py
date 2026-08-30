from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.repositories import AuditRepository
from app.api.v1.cases import get_case_service
from app.main import create_app
from app.services.case_service import CaseService


def test_create_audit_failure_returns_structured_error_without_persistence(
    db_session: Session,
    valid_payload: dict[str, object],
) -> None:
    app = create_app()

    def failing_service() -> CaseService:
        return CaseService(
            db_session,
            audit_repository=AuditRepository(db_session, fail_writes=True),
        )

    app.dependency_overrides[get_case_service] = failing_service
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cases",
            json=valid_payload,
            headers={
                "Idempotency-Key": "idem-audit-failure",
                "X-Correlation-ID": "corr-audit-failure",
            },
        )
    assert response.status_code == 500
    assert response.json()["error_code"] == "AUDIT_APPEND_FAILED"
    assert response.json()["correlation_id"] == "corr-audit-failure"
    assert CaseService(db_session).case_count() == 0


def test_evidence_idempotency_conflict_has_no_additional_side_effect(
    client: TestClient,
    valid_payload: dict[str, object],
) -> None:
    payload = deepcopy(valid_payload)
    payload["evidence_metadata"] = []
    created = client.post(
        "/api/v1/cases",
        json=payload,
        headers={"Idempotency-Key": "idem-evidence-conflict-case"},
    )
    case_id = created.json()["case_id"]
    evidence = {
        "evidence_type": "receipt",
        "file_name": "receipt.png",
        "content_type": "image/png",
        "size_bytes": 100,
        "checksum_sha256": "d" * 64,
        "uploader_ref": "customer:cust_1001",
    }
    headers = {"Idempotency-Key": "idem-evidence-conflict", "If-Match": "1"}
    accepted = client.post(
        f"/api/v1/cases/{case_id}/evidence", json=evidence, headers=headers
    )
    changed = dict(evidence)
    changed["file_name"] = "different.png"
    conflict = client.post(
        f"/api/v1/cases/{case_id}/evidence", json=changed, headers=headers
    )

    assert accepted.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert client.get(f"/api/v1/cases/{case_id}/evidence").json()["total"] == 1
    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert sum(
        event["event_type"] == "EVIDENCE_METADATA_REGISTERED"
        for event in detail["audit_events"]
    ) == 1
