"""Offline independent golden expectations for control configuration promotion."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.domain.controls import ControlProfile, EvidenceItem, digest
from app.services.case_confidence import ConfidenceService, rule_certainty
from app.services.evidence_completeness import EvidenceCompletenessService
from app.services.rules_engine import RulesEngine

FIXTURES = Path(__file__).parent / "fixtures"


def load_profile() -> ControlProfile:
    return ControlProfile.model_validate_json((FIXTURES / "controls-v1.json").read_text())


def golden_inputs() -> dict[str, Any]:
    facts: dict[str, Any] = {
        "customer_ref": "customer-a",
        "dispute_type": "duplicate_card_transaction",
        "submitted_at": "2026-01-02T00:00:00Z",
        "account": {
            "customer_ref": "customer-a",
            "account_ref": "account-a",
            "status": "active",
            "product": "card",
        },
        "references": ["provider:txn-a:v1", "provider:txn-b:v1"],
    }
    for name, ref in (("disputed", "txn-a"), ("candidate", "txn-b")):
        facts[name] = {
            "transaction_ref": ref,
            "account_ref": "account-a",
            "merchant_ref": "merchant-a",
            "currency": "USD",
            "amount": "49.99",
            "authorized_at": "2026-01-01T00:00:00Z",
        }
        facts[f"{name}_settlement"] = {"transaction_ref": ref, "status": "settled"}
        facts[f"{name}_refund"] = {
            "transaction_ref": ref,
            "status": "not_refunded",
            "amount": "0.00",
            "currency": "USD",
        }
    return {"facts": facts, "signals": {"classification": "0.9", "policy": "0.8"}}


def evaluate_profile(profile: ControlProfile) -> dict[str, Any]:
    dataset = json.loads((FIXTURES / "controls-golden-v1.json").read_text())
    failures: list[dict[str, Any]] = []
    at = datetime(2026, 1, 2, tzinfo=UTC)
    for case in dataset["cases"]:
        if "invalid_config" in case:
            invalid = profile.model_dump(mode="json")
            target = invalid
            path = case["invalid_config"]["path"].split(".")
            for part in path[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            target[path[-1]] = case["invalid_config"]["value"]
            try:
                ControlProfile.model_validate(invalid)
            except ValueError:
                continue
            failures.append({"scenario": case["id"], "expected": "invalid configuration"})
            continue
        inputs = copy.deepcopy(golden_inputs())
        for path, value in case["changes"].items():
            target = inputs
            parts = path.split(".")
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
        items = [
            EvidenceItem(
                reference=r.requirement_id,
                kind=r.kinds[0],
                checksum=digest(r.requirement_id),
                state="validated",
                source_as_of=at - timedelta(days=2) if case.get("stale") else at,
            )
            for r in profile.evidence.requirements
            if r.requirement_id != case.get("remove_evidence")
        ]
        evidence = EvidenceCompletenessService().assess(profile.evidence, items, at)
        if case.get("conflict"):
            item = items[0].model_copy(
                update={"subject": "same-record", "attributes": {"currency": "USD"}}
            )
            items[0] = item
            items.append(
                item.model_copy(
                    update={
                        "reference": "conflicting-record",
                        "attributes": {"currency": "EUR"},
                    }
                )
            )
            evidence = EvidenceCompletenessService().assess(profile.evidence, items, at)

        class FailingEngine(RulesEngine):
            def _evaluate(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("Injected golden handler exception")

        engine = FailingEngine() if case.get("rule_exception") else RulesEngine()
        rules = engine.execute(
            profile.rules,
            inputs["facts"],
            evidence,
            case.get("policy_refs", ["POL-DUP-CARD-CONTROLS:2026.09"]),
            at,
        )
        signals = inputs["signals"] | {
            "evidence": evidence.score,
            "rules": rule_certainty(rules),
            "conflicts": int(bool(evidence.conflicting)),
            "tools": 0,
        }
        gates = ["RULE_REVIEW"] if rules.blocked else []
        if not evidence.mandatory_complete:
            gates.append("MANDATORY_EVIDENCE_INCOMPLETE")
        confidence = ConfidenceService().evaluate(
            profile.confidence, signals, {key: "golden:record-v1" for key in signals}, gates
        )
        actual = {
            "candidate": rules.candidate,
            "mandatory_complete": evidence.mandatory_complete,
            "score": str(confidence.score),
            "ready": confidence.ready,
        }
        for key in actual:
            if key in case and case[key] != actual[key]:
                failures.append(
                    {
                        "scenario": case["id"],
                        "field": key,
                        "expected": case[key],
                        "actual": actual[key],
                    }
                )
    return {
        "dataset_version": dataset["dataset_version"],
        "dataset_hash": digest(dataset),
        "profile_hash": digest(profile),
        "scenario_count": len(dataset["cases"]),
        "passed": not failures,
        "failures": failures,
    }


if __name__ == "__main__":
    report = evaluate_profile(load_profile())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
