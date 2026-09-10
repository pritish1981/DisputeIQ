from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.control_repository import ControlConfigurationError, ControlRepository
from app.control_regression import evaluate_profile, golden_inputs, load_profile
from app.domain.controls import ControlProfile, EvidenceItem, ReevaluationRequest, digest
from app.services.case_confidence import ConfidenceService
from app.services.control_registry import ControlRegistry
from app.services.evidence_completeness import EvidenceCompletenessService
from app.services.rules_engine import RulesEngine


def test_golden_regression() -> None:
    assert evaluate_profile(load_profile())["passed"]


@pytest.mark.parametrize(
    "mutation",
    [
        "handler",
        "parameter",
        "timestamp",
        "empty",
        "weights",
        "production",
        "duplicate",
    ],
)
def test_invalid_configuration(mutation: str) -> None:
    data = load_profile().model_dump(mode="json")
    if mutation == "handler":
        data["rules"]["rules"][0]["handler"] = "eval"
    elif mutation == "parameter":
        data["rules"]["rules"][1]["parameters"]["filing_days"] = -1
    elif mutation == "timestamp":
        data["effective_from"] = "2026-01-01T00:00:00"
    elif mutation == "empty":
        data["evidence"]["requirements"] = []
    elif mutation == "weights":
        data["confidence"]["weights"]["classification"] = "NaN"
    elif mutation == "production":
        data["environment"] = "production"
    else:
        data["evidence"]["requirements"].append(data["evidence"]["requirements"][0])
    with pytest.raises(ValidationError):
        ControlProfile.model_validate(data)


def test_canonical_inputs() -> None:
    assert digest({"a": [1, 2], "b": Decimal("1.00")}) == digest({"b": Decimal("1"), "a": [2, 1]})
    assert digest({"version": "v1"}) != digest({"version": "v2"})
    with pytest.raises(ValueError):
        digest(float("nan"))
    with pytest.raises(ValueError):
        digest(datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        ReevaluationRequest.model_validate(
            {"prior_evaluation_id": "a" * 36, "reason": "x", "approved": True}
        )


def test_registry_is_immutable_and_regression_gated(db_session: Session) -> None:
    profile = load_profile()
    registry = ControlRegistry(db_session)
    row = registry.register(profile, "test:admin")
    assert registry.register(profile, "test:admin").config_id == row.config_id
    data = profile.model_dump(mode="json")
    data["confidence"]["threshold"] = "0.99"
    with pytest.raises(ControlConfigurationError, match="REGRESSION_FAILED"):
        registry.register(ControlProfile.model_validate(data), "test:admin")
    data = profile.model_dump(mode="json")
    data["approval_ref"] = "changed"
    with pytest.raises(ControlConfigurationError, match="IMMUTABLE"):
        registry.register(ControlProfile.model_validate(data), "test:admin")
    repository = ControlRepository(db_session)
    with pytest.raises(ControlConfigurationError, match="PINNED_CONFIGURATION_UNAVAILABLE"):
        repository.profile("missing-version")
    assert (
        repository.resolve(
            environment="local",
            dispute_type=profile.dispute_type,
            product="card",
            channel="web",
            jurisdiction="US",
            at=datetime(2026, 9, 8, tzinfo=UTC),
        )[0]
        == row.config_id
    )
    data["version"] = "controls-v2"
    registry.register(ControlProfile.model_validate(data), "test:admin")
    with pytest.raises(ControlConfigurationError, match="NO_UNIQUE"):
        repository.resolve(
            environment="local",
            dispute_type=profile.dispute_type,
            product="card",
            channel="web",
            jurisdiction="US",
            at=datetime(2026, 9, 8, tzinfo=UTC),
        )


def test_freshness_validation_and_conflict() -> None:
    profile = load_profile()
    at = datetime(2026, 9, 8, tzinfo=UTC)
    item = EvidenceItem(
        reference="a",
        kind="disputed",
        checksum="a",
        state="validated",
        source_as_of=at - timedelta(days=1),
        subject="txn-a",
        attributes={"currency": "USD"},
    )
    service = EvidenceCompletenessService()
    assert not service.assess(profile.evidence, [item], at).stale
    stale = service.assess(profile.evidence, [item], at + timedelta(seconds=1))
    assert stale.stale == ["a"]
    unknown = service.assess(profile.evidence, [item.model_copy(update={"state": "unknown"})], at)
    assert "a" in unknown.available and "a" in unknown.invalid
    assert "disputed" not in unknown.missing
    conflict = item.model_copy(update={"reference": "b", "attributes": {"currency": "EUR"}})
    result = service.assess(profile.evidence, [item, conflict], at)
    assert result.conflicting == ["a", "b"]
    assert not result.satisfaction["disputed"]
    future = item.model_copy(update={"source_as_of": at + timedelta(seconds=1)})
    assert service.assess(profile.evidence, [future], at).invalid == ["a"]
    missing_time = item.model_copy(update={"source_as_of": None})
    assert service.assess(profile.evidence, [missing_time], at).invalid == ["a"]


def test_duplicate_upload_does_not_inflate_score() -> None:
    profile = load_profile()
    item = EvidenceItem(reference="a", kind="receipt", checksum="same", state="validated")
    service = EvidenceCompletenessService()
    at = datetime(2026, 9, 8, tzinfo=UTC)
    first = service.assess(profile.evidence, [item], at)
    second = service.assess(
        profile.evidence, [item, item.model_copy(update={"reference": "b"})], at
    )
    assert first.score == second.score == Decimal("0.142857")
    assert not second.mandatory_complete


def test_optional_and_unrelated_evidence_cannot_bypass_mandatory_gate() -> None:
    from app.domain.controls import EvidenceContract, EvidenceRequirement

    contract = EvidenceContract(
        version="optional-test",
        requirements=(
            EvidenceRequirement(requirement_id="required", kinds=("receipt",)),
            EvidenceRequirement(requirement_id="optional", kinds=("extra",), mandatory=False),
        ),
    )
    at = datetime(2026, 9, 8, tzinfo=UTC)
    required = EvidenceItem(reference="a", kind="receipt", checksum="a", state="validated")
    unrelated = EvidenceItem(reference="b", kind="unrelated", checksum="b", state="validated")
    service = EvidenceCompletenessService()
    result = service.assess(contract, [required, unrelated], at)
    assert result.score == Decimal("0.5") and result.mandatory_complete
    result = service.assess(contract, [unrelated], at)
    assert result.score == 0 and not result.mandatory_complete


def test_pinned_rule_recomputation_is_independent_of_fact_order() -> None:
    profile = load_profile()
    at = datetime(2026, 9, 8, tzinfo=UTC)
    facts = golden_inputs()["facts"]
    evidence = EvidenceCompletenessService().assess(profile.evidence, [], at)
    engine = RulesEngine()
    original = engine.execute(profile.rules, facts, evidence, [], at)
    reordered = dict(reversed(list(facts.items())))
    reordered["references"] = list(reversed(facts["references"]))
    assert engine.execute(profile.rules, reordered, evidence, [], at) == original
    assert engine.execute(
        profile.rules, facts, evidence, [], at + timedelta(seconds=1)
    ).facts_hash != (original.facts_hash)


def test_confidence_unknown_and_mandatory_gate() -> None:
    profile = load_profile()
    signals: dict[str, Any] = dict(
        classification=1, evidence=1, policy=1, rules=1, conflicts=0, tools=0
    )
    refs = {key: "ref" for key in signals}
    service = ConfidenceService()
    result = service.evaluate(profile.confidence, signals, refs, ["MANDATORY_EVIDENCE_INCOMPLETE"])
    assert result.score == 1 and not result.ready
    for value in (None, float("inf"), -1, 2):
        result = service.evaluate(profile.confidence, signals | {"policy": value}, refs, [])
        assert not result.ready and "UNKNOWN_SIGNAL:policy" in result.reasons
        assert result.factors["policy"].weight == Decimal("0.25")


def test_rule_exception_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any) -> Any:
        raise RuntimeError("sensitive internal failure")

    engine = RulesEngine()
    monkeypatch.setattr(engine, "_evaluate", broken)
    profile = load_profile()
    at = datetime(2026, 9, 8, tzinfo=UTC)
    evidence = EvidenceCompletenessService().assess(profile.evidence, [], at)
    result = engine.execute(profile.rules, golden_inputs()["facts"], evidence, [], at)
    assert result.blocked and result.candidate == "REVIEW_REQUIRED"
    assert {r.reason_code for r in result.results} == {"RULE_EXECUTION_ERROR"}
    assert "sensitive" not in result.model_dump_json()
