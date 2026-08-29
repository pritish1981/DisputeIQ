from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.schemas import CreateDisputeRequest, DisputeType


def test_create_dispute_schema_accepts_valid_payload(valid_payload: dict[str, object]) -> None:
    request = CreateDisputeRequest.model_validate(valid_payload)

    assert request.customer_ref == "cust_1001"
    assert request.transaction_ref == "txn_3001"
    assert request.dispute_type is DisputeType.duplicate_card_transaction


def test_create_dispute_schema_rejects_short_description(
    valid_payload: dict[str, object],
) -> None:
    valid_payload["description"] = "short"

    with pytest.raises(ValidationError) as exc_info:
        CreateDisputeRequest.model_validate(valid_payload)

    assert "description" in str(exc_info.value)


def test_create_dispute_schema_rejects_bad_evidence_checksum(
    valid_payload: dict[str, object],
) -> None:
    evidence = valid_payload["evidence_metadata"]
    assert isinstance(evidence, list)
    evidence[0]["checksum_sha256"] = "bad"

    with pytest.raises(ValidationError) as exc_info:
        CreateDisputeRequest.model_validate(valid_payload)

    assert "checksum_sha256" in str(exc_info.value)
