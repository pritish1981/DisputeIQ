"""Versioned, data-only deterministic control contracts (FR-EVD/RUL/CNF)."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

CONTROL_GRAPH_VERSION = "duplicate-card-controls-v1"
Score = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(UTC)


def canonical(value: Any) -> Any:
    """Collections in control snapshots are sets; rule order is an explicit integer."""
    if isinstance(value, BaseModel):
        return canonical(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        return utc(value).isoformat()
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite value")
        return format(value.normalize(), "f")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite value")
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return sorted((canonical(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Unsupported canonical type: {type(value).__name__}")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRequirement(Contract):
    requirement_id: str = Field(min_length=1)
    kinds: tuple[str, ...] = Field(min_length=1)
    mandatory: bool = True
    minimum_count: int = Field(default=1, ge=1)
    weight: int = Field(default=1, ge=1)
    maximum_age_seconds: int | None = Field(default=None, ge=0)
    accepted_states: tuple[Literal["validated"], ...] = ("validated",)


class EvidenceContract(Contract):
    version: str = Field(min_length=1)
    requirements: tuple[EvidenceRequirement, ...] = Field(min_length=1)
    conflict_fields: tuple[str, ...] = (
        "account_ref",
        "customer_ref",
        "currency",
        "transaction_ref",
        "status",
        "amount",
    )

    @model_validator(mode="after")
    def unique_requirements(self) -> Self:
        if len({r.requirement_id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Duplicate evidence requirement")
        return self


class PolicyMapping(Contract):
    document_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    family: str = Field(min_length=1)
    dispute_type: str = Field(min_length=1)


class EligibilityProfile(Contract):
    version: str = Field(min_length=1)
    family: str = Field(min_length=1)
    mappings: tuple[PolicyMapping, ...] = Field(min_length=1)


RuleHandler = Literal["eligibility", "timeline", "evidence", "policy", "duplicate", "remediation"]


class RuleDefinition(Contract):
    rule_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    handler: RuleHandler
    order: int = Field(ge=0)
    mandatory: bool = True
    dispute_type: str = "duplicate_card_transaction"
    effective_from: AwareDatetime
    effective_to: AwareDatetime | None = None
    parameters: dict[str, Decimal] = Field(default_factory=dict)
    policy_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_parameters(self) -> Self:
        expected = {"timeline": {"filing_days"}, "duplicate": {"window_seconds"}}.get(
            self.handler, set()
        )
        if set(self.parameters) != expected:
            raise ValueError("Invalid rule parameters")
        if any(not v.is_finite() or v < 0 for v in self.parameters.values()):
            raise ValueError("Invalid rule parameter range")
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Invalid effective interval")
        return self


class RuleSet(Contract):
    version: str = Field(min_length=1)
    rules: tuple[RuleDefinition, ...] = Field(min_length=1)
    disposition_version: Literal["duplicate-disposition-v1"] = "duplicate-disposition-v1"

    @model_validator(mode="after")
    def unique_rules(self) -> Self:
        for values in ([r.rule_id for r in self.rules], [r.order for r in self.rules]):
            if len(set(values)) != len(values):
                raise ValueError("Duplicate rule identity/order")
        if {r.handler for r in self.rules} != {
            "eligibility",
            "timeline",
            "evidence",
            "policy",
            "duplicate",
            "remediation",
        }:
            raise ValueError("Required control handlers missing")
        return self


class ConfidenceConfig(Contract):
    version: str = Field(min_length=1)
    formula: Literal["weighted-penalties-v1"] = "weighted-penalties-v1"
    weights: dict[str, Score]
    penalties: dict[str, Score]
    threshold: Score
    decimal_places: Literal[6] = 6
    rounding: Literal["ROUND_HALF_UP"] = "ROUND_HALF_UP"

    @model_validator(mode="after")
    def valid_formula(self) -> Self:
        if set(self.weights) != {"classification", "evidence", "policy", "rules"}:
            raise ValueError("Missing confidence weight")
        if set(self.penalties) != {"conflicts", "tools"}:
            raise ValueError("Missing confidence penalty")
        if sum(self.weights.values()) != 1:
            raise ValueError("Confidence weights must sum to one")
        return self


class ControlProfile(Contract):
    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    synthetic: bool = True
    approval_ref: str = Field(min_length=1)
    effective_from: AwareDatetime
    effective_to: AwareDatetime | None = None
    dispute_type: str = "duplicate_card_transaction"
    product: str = Field(min_length=1)
    channels: tuple[str, ...] = Field(min_length=1)
    jurisdictions: tuple[str, ...] = Field(min_length=1)
    evidence: EvidenceContract
    eligibility: EligibilityProfile
    rules: RuleSet
    confidence: ConfidenceConfig

    @model_validator(mode="after")
    def valid_profile(self) -> Self:
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Invalid profile interval")
        if self.synthetic and self.environment not in {"local", "test"}:
            raise ValueError("Synthetic controls cannot be activated in production")
        refs = {f"{p.document_id}:{p.version}" for p in self.eligibility.mappings}
        if any(not set(r.policy_refs) <= refs for r in self.rules.rules):
            raise ValueError("Rule policy references do not match profile")
        return self


class EvidenceItem(Contract):
    reference: str
    kind: str
    checksum: str
    state: Literal["validated", "unknown", "invalid", "unavailable"]
    source_as_of: AwareDatetime | None = None
    subject: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class EvidenceAssessment(Contract):
    contract_version: str
    snapshot_hash: str
    required: list[str]
    available: list[str]
    missing: list[str]
    stale: list[str]
    invalid: list[str]
    conflicting: list[str]
    satisfaction: dict[str, list[str]]
    reasons: list[str]
    score: Score
    mandatory_complete: bool


class RuleOutcome(StrEnum):
    passed = "PASS"
    failed = "FAIL"
    not_applicable = "NOT_APPLICABLE"
    indeterminate = "INDETERMINATE"
    error = "ERROR"


class RuleResult(Contract):
    rule_id: str
    version: str
    outcome: RuleOutcome
    reason_code: str
    mandatory: bool
    fact_refs: list[str]
    policy_refs: tuple[str, ...]
    config_ref: str


class RuleExecution(Contract):
    ruleset_version: str
    facts_hash: str
    results: list[RuleResult]
    candidate: Literal[
        "DUPLICATE_SUPPORTED", "DUPLICATE_NOT_SUPPORTED", "ALREADY_REMEDIATED", "REVIEW_REQUIRED"
    ]
    blocked: bool


class ConfidenceFactor(Contract):
    raw: str | None
    normalized: Score
    weight: Decimal
    contribution: Decimal
    source_ref: str
    valid: bool


class ConfidenceEvaluation(Contract):
    config_version: str
    factors: dict[str, ConfidenceFactor]
    score: Score
    threshold: Score
    reasons: list[str]
    ready: bool
    pins: dict[str, Any] = Field(default_factory=dict)


class ReevaluationRequest(Contract):
    prior_evaluation_id: str = Field(min_length=36, max_length=36)
    reason: str = Field(min_length=1, max_length=240)
    retain_pins: bool = True


class EvaluationBundle(Contract):
    case_id: str
    workflow_id: str
    state_version: int
    graph_version: Literal["duplicate-card-controls-v1"] = "duplicate-card-controls-v1"
    evaluated_at: AwareDatetime
    profile_id: str | None
    profile_version: str | None
    profile_hash: str | None
    inputs_hash: str
    classification_hash: str
    evidence_hash: str
    facts_hash: str
    versions: dict[str, str]
    prior_evaluation_id: str | None = None
    reevaluation_reason: str | None = None


class ReviewRequestOut(Contract):
    request_id: str
    kind: str
    required_role: str
    reasons: list[str]
    required_items: list[str]
    status: str
    fulfilled_by: str | None = None


class ControlEvaluationOut(Contract):
    evaluation_id: str
    bundle: EvaluationBundle
    stages: dict[str, Any]
    requests: list[ReviewRequestOut]


class ControlEvaluationList(Contract):
    items: list[ControlEvaluationOut]
