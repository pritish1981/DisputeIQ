from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    CaseStatus,
    CreateCaseRequest,
    DisputeType,
    parse_if_match,
    validate_case_transition,
)


def test_create_case_schema_accepts_phase_002_payload(
    valid_payload: dict[str, object],
) -> None:
    request = CreateCaseRequest.model_validate(valid_payload)
    assert request.customer_ref == "cust_1001"
    assert request.transaction_ref == "txn_3001"
    assert request.dispute_type is DisputeType.duplicate_card_transaction


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "short"),
        ("transaction_ref", "bad reference!"),
        ("dispute_type", "failed_upi_transfer"),
    ],
)
def test_create_case_schema_rejects_invalid_or_unsupported_values(
    valid_payload: dict[str, object],
    field: str,
    value: str,
) -> None:
    payload = deepcopy(valid_payload)
    payload[field] = value
    with pytest.raises(ValidationError):
        CreateCaseRequest.model_validate(payload)


def test_evidence_metadata_validation_rejects_checksum_and_content_type(
    valid_payload: dict[str, object],
) -> None:
    payload = deepcopy(valid_payload)
    evidence = payload["evidence_metadata"]
    assert isinstance(evidence, list)
    evidence[0]["checksum_sha256"] = "bad"
    evidence[0]["content_type"] = "invalid"
    with pytest.raises(ValidationError) as exc_info:
        CreateCaseRequest.model_validate(payload)
    assert "checksum_sha256" in str(exc_info.value)
    assert "content_type" in str(exc_info.value)


def test_phase_002_lifecycle_and_if_match_controls() -> None:
    validate_case_transition(CaseStatus.draft, CaseStatus.submitted)
    with pytest.raises(ValueError):
        validate_case_transition(CaseStatus.submitted, CaseStatus.closed)
    assert parse_if_match('W/"2"') == 2
    with pytest.raises(ValueError):
        parse_if_match("not-a-version")
