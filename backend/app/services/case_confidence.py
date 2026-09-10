from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.domain.controls import (
    ConfidenceConfig,
    ConfidenceEvaluation,
    ConfidenceFactor,
    RuleExecution,
    RuleOutcome,
)


def rule_certainty(execution: RuleExecution) -> Decimal | None:
    applicable = [r for r in execution.results if r.outcome != RuleOutcome.not_applicable]
    if not applicable:
        return None
    return Decimal(
        sum(r.outcome in {RuleOutcome.passed, RuleOutcome.failed} for r in applicable)
    ) / (len(applicable))


class ConfidenceService:
    def evaluate(
        self,
        config: ConfidenceConfig,
        signals: dict[str, Any],
        source_refs: dict[str, str],
        hard_gates: list[str],
    ) -> ConfidenceEvaluation:
        factors: dict[str, ConfidenceFactor] = {}
        reasons = set(hard_gates)
        score = Decimal(0)
        for name, weight in (
            config.weights | {name: -value for name, value in config.penalties.items()}
        ).items():
            raw = signals.get(name)
            valid = True
            try:
                normalized = Decimal(str(raw))
                valid = (
                    normalized.is_finite() and 0 <= normalized <= 1 and bool(source_refs.get(name))
                )
            except (InvalidOperation, ValueError, TypeError):
                valid = False
                normalized = Decimal(0)
            if not valid:
                normalized = Decimal(0)
                reasons.add(f"UNKNOWN_SIGNAL:{name}")
            contribution = normalized * weight
            score += contribution
            factors[name] = ConfidenceFactor(
                raw=str(raw) if raw is not None else None,
                normalized=normalized,
                weight=weight,
                contribution=contribution,
                source_ref=source_refs.get(name, ""),
                valid=valid,
            )
        score = min(Decimal(1), max(Decimal(0), score)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        if score < config.threshold:
            reasons.add("LOW_CASE_CONFIDENCE")
        return ConfidenceEvaluation(
            config_version=config.version,
            factors=factors,
            score=score,
            threshold=config.threshold,
            reasons=sorted(reasons),
            ready=not reasons,
        )
