"""Pure rule handlers. No database, model, provider, or clock dependencies."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.controls import (
    EvidenceAssessment,
    RuleDefinition,
    RuleExecution,
    RuleOutcome,
    RuleResult,
    RuleSet,
    digest,
    utc,
)


def instant(value: Any) -> datetime:
    return utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))


def money(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Invalid monetary fact")
    return result


class RulesEngine:
    def execute(
        self,
        ruleset: RuleSet,
        facts: dict[str, Any],
        evidence: EvidenceAssessment,
        policy_refs: list[str],
        as_of: datetime,
    ) -> RuleExecution:
        at = utc(as_of)
        results: list[RuleResult] = []
        for rule in sorted(ruleset.rules, key=lambda r: r.order):
            try:
                if not rule.effective_from <= at or (
                    rule.effective_to is not None and at > rule.effective_to
                ):
                    outcome, reason = RuleOutcome.error, "RULE_VERSION_NOT_EFFECTIVE"
                elif rule.dispute_type != facts.get("dispute_type"):
                    outcome, reason = RuleOutcome.not_applicable, "RULE_NOT_APPLICABLE"
                else:
                    outcome, reason = self._evaluate(rule, facts, evidence, policy_refs)
            except KeyError:
                outcome, reason = RuleOutcome.indeterminate, "MISSING_AUTHORITATIVE_FACTS"
            except (ValueError, TypeError, ArithmeticError):
                outcome, reason = RuleOutcome.indeterminate, "INVALID_AUTHORITATIVE_FACTS"
            except Exception:
                outcome, reason = RuleOutcome.error, "RULE_EXECUTION_ERROR"
            results.append(
                RuleResult(
                    rule_id=rule.rule_id,
                    version=rule.version,
                    outcome=outcome,
                    reason_code=reason,
                    mandatory=rule.mandatory,
                    fact_refs=sorted(str(ref) for ref in facts.get("references", [])),
                    policy_refs=rule.policy_refs,
                    config_ref=ruleset.version,
                )
            )
        blocked = bool(evidence.conflicting) or any(
            r.mandatory and r.outcome in {RuleOutcome.indeterminate, RuleOutcome.error}
            for r in results
        )
        if not any(r.outcome != RuleOutcome.not_applicable for r in results):
            blocked = True
        candidate: Any = "DUPLICATE_SUPPORTED"
        if blocked:
            candidate = "REVIEW_REQUIRED"
        elif any(r.reason_code == "ALREADY_REMEDIATED" for r in results):
            candidate = "ALREADY_REMEDIATED"
        elif any(r.outcome == RuleOutcome.failed for r in results):
            candidate = "DUPLICATE_NOT_SUPPORTED"
        return RuleExecution(
            ruleset_version=ruleset.version,
            facts_hash=digest(
                {"facts": facts, "evidence": evidence, "policy_refs": policy_refs, "as_of": at}
            ),
            results=results,
            candidate=candidate,
            blocked=blocked,
        )

    def _evaluate(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        evidence: EvidenceAssessment,
        policy_refs: list[str],
    ) -> tuple[RuleOutcome, str]:
        handler = rule.handler
        if handler == "evidence":
            return (
                (RuleOutcome.passed, "MANDATORY_EVIDENCE_COMPLETE")
                if (evidence.mandatory_complete)
                else (RuleOutcome.indeterminate, "MANDATORY_EVIDENCE_INCOMPLETE")
            )
        if handler == "policy":
            return (
                (RuleOutcome.passed, "CITED_POLICY_ADMITTED")
                if (set(rule.policy_refs) <= set(policy_refs))
                else (RuleOutcome.indeterminate, "POLICY_PROFILE_MISMATCH")
            )
        first, second = facts["disputed"], facts["candidate"]
        if not first or not second:
            return RuleOutcome.indeterminate, "MISSING_AUTHORITATIVE_FACTS"
        for transaction in (first, second):
            for key in (
                "transaction_ref",
                "account_ref",
                "merchant_ref",
                "currency",
                "authorized_at",
            ):
                if not isinstance(transaction[key], str) or not transaction[key].strip():
                    return RuleOutcome.indeterminate, "INVALID_AUTHORITATIVE_FACTS"
        if first["transaction_ref"] == second["transaction_ref"]:
            return RuleOutcome.indeterminate, "NO_DISTINCT_TRANSACTION_PAIR"
        if handler == "eligibility":
            account = facts["account"]
            valid = (
                account["customer_ref"] == facts["customer_ref"]
                and account["account_ref"] == first["account_ref"] == second["account_ref"]
                and account["status"] == "active"
                and account["product"] == "card"
                and first["transaction_ref"] != second["transaction_ref"]
            )
            return self._result(valid, "ELIGIBLE_CARD_PAIR", "INELIGIBLE_CARD_PAIR")
        if handler == "timeline":
            elapsed = instant(facts["submitted_at"]) - instant(first["authorized_at"])
            seconds = Decimal(str(elapsed.total_seconds()))
            return self._result(
                0 <= seconds <= rule.parameters["filing_days"] * 86400,
                "WITHIN_FILING_WINDOW",
                "OUTSIDE_FILING_WINDOW",
            )
        if handler == "duplicate":
            same = (
                all(
                    first[key] == second[key] for key in ("account_ref", "merchant_ref", "currency")
                )
                and first["transaction_ref"] != second["transaction_ref"]
            )
            delta = abs(
                (instant(first["authorized_at"]) - instant(second["authorized_at"])).total_seconds()
            )
            match = (
                same
                and money(first["amount"]) == money(second["amount"])
                and (Decimal(str(delta)) <= rule.parameters["window_seconds"])
            )
            return self._result(match, "DUPLICATE_PAIR_MATCH", "DUPLICATE_PAIR_NONMATCH")
        # Remediation is evaluated for both transaction records.
        remedied = False
        for name, transaction in (("disputed", first), ("candidate", second)):
            settlement, refund = facts[f"{name}_settlement"], facts[f"{name}_refund"]
            if settlement["transaction_ref"] != transaction["transaction_ref"] or (
                refund["transaction_ref"] != transaction["transaction_ref"]
                or refund["currency"] != transaction["currency"]
            ):
                return RuleOutcome.indeterminate, "CONFLICTING_REMEDIATION_FACTS"
            amount = money(refund["amount"])
            full = money(transaction["amount"])
            if settlement["status"] == "reversed" or (
                refund["status"] == "refunded" and amount == full
            ):
                remedied = True
            elif settlement["status"] != "settled" or (
                refund["status"] != "not_refunded" or amount != 0
            ):
                return RuleOutcome.indeterminate, "UNRESOLVED_REMEDIATION"
        if remedied:
            return RuleOutcome.failed, "ALREADY_REMEDIATED"
        return RuleOutcome.passed, "NO_EXISTING_REMEDIATION"

    @staticmethod
    def _result(value: bool, passed: str, failed: str) -> tuple[RuleOutcome, str]:
        return (RuleOutcome.passed, passed) if value else (RuleOutcome.failed, failed)
