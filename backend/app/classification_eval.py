from __future__ import annotations

import json

from fastapi.encoders import jsonable_encoder

from app.core.config import settings
from app.domain.schemas import ClassificationInput, ModelGatewayFailureReason
from app.services.classification import ClassificationService
from app.services.model_gateway import DeterministicClassificationProvider, ModelGateway


def _input(description: str, correlation_id: str) -> ClassificationInput:
    return ClassificationInput(
        description=description,
        transaction_ref="txn_eval",
        channel="web",
        evidence_count=1,
        correlation_id=correlation_id,
    )


def main() -> None:
    service = ClassificationService()
    cases = [
        ("duplicate_card", _input("Duplicate card transaction at merchant.", "eval-dup")),
        ("failed_upi", _input("Failed UPI transfer not credited.", "eval-upi")),
        ("atm_cash", _input("ATM debit happened but cash was not dispensed.", "eval-atm")),
        ("unsupported", _input("Hotel booking cancellation issue.", "eval-unsupported")),
    ]
    results: dict[str, object] = {}
    passed = True
    for name, request in cases:
        decision = service.classify(request)
        results[name] = {
            "accepted": decision.accepted,
            "category": decision.output.category if decision.output is not None else None,
            "confidence": decision.output.confidence if decision.output is not None else None,
            "manual_classification_required": decision.manual_classification_required,
            "reason": decision.reason,
            "threshold": decision.threshold,
            "telemetry": decision.telemetry.model_dump(mode="json"),
        }
        if name == "unsupported":
            passed = passed and decision.reason is ModelGatewayFailureReason.unsupported_category
        else:
            passed = passed and decision.accepted

    low_confidence = ClassificationService(
        gateway=ModelGateway(provider=DeterministicClassificationProvider(mode="low_confidence"))
    ).classify(_input("Duplicate card transaction at merchant.", "eval-low"))
    killed_settings = settings.__class__(ai_kill_switch_enabled=True)
    kill_switch = ClassificationService(app_settings=killed_settings).classify(
        _input("Duplicate card transaction at merchant.", "eval-kill")
    )
    fallback = ClassificationService(
        gateway=ModelGateway(
            provider=DeterministicClassificationProvider(mode="timeout"),
            fallback_provider=DeterministicClassificationProvider(
                provider_ref="deterministic-fallback"
            ),
        )
    ).classify(_input("Duplicate card transaction at merchant.", "eval-fallback"))
    malformed = ClassificationService(
        gateway=ModelGateway(provider=DeterministicClassificationProvider(mode="malformed"))
    ).classify(_input("Duplicate card transaction at merchant.", "eval-malformed"))

    results["low_confidence"] = {
        "accepted": low_confidence.accepted,
        "reason": low_confidence.reason,
    }
    results["kill_switch"] = {
        "accepted": kill_switch.accepted,
        "reason": kill_switch.reason,
    }
    results["fallback"] = {
        "accepted": fallback.accepted,
        "fallback_used": fallback.telemetry.fallback_used,
    }
    results["malformed"] = {
        "accepted": malformed.accepted,
        "reason": malformed.reason,
    }
    passed = (
        passed
        and low_confidence.reason is ModelGatewayFailureReason.low_confidence
        and kill_switch.reason is ModelGatewayFailureReason.ai_kill_switch
        and fallback.accepted
        and fallback.telemetry.fallback_used
        and malformed.reason is ModelGatewayFailureReason.schema_validation_failed
    )
    payload = {
        "evaluation": "classification-eval-v1",
        "passed": passed,
        "thresholds": {
            "minimum_confidence": settings.classification_confidence_threshold,
            "schema_validity_required": True,
            "manual_route_required_for_unsupported": True,
        },
        "results": results,
    }
    print(json.dumps(jsonable_encoder(payload), indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
