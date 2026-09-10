from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.domain.controls import EvidenceAssessment, EvidenceContract, EvidenceItem, digest, utc


class EvidenceCompletenessService:
    def assess(
        self, contract: EvidenceContract, items: list[EvidenceItem], evaluated_at: datetime
    ) -> EvidenceAssessment:
        at = utc(evaluated_at)
        conflicts: set[str] = set()
        for index, left in enumerate(items):
            for right in items[index + 1 :]:
                if not left.subject or left.subject != right.subject:
                    continue
                if any(
                    key in left.attributes
                    and key in right.attributes
                    and left.attributes[key] != right.attributes[key]
                    for key in contract.conflict_fields
                ):
                    conflicts.update((left.reference, right.reference))
        satisfaction: dict[str, list[str]] = {}
        missing: list[str] = []
        stale: set[str] = set()
        invalid: set[str] = set()
        reasons: set[str] = set()
        earned = 0
        mandatory_complete = True
        for requirement in contract.requirements:
            matching = [item for item in items if item.kind in requirement.kinds]
            accepted: dict[str, str] = {}
            for item in sorted(matching, key=lambda item: item.reference):
                if item.state not in requirement.accepted_states or not item.checksum:
                    invalid.add(item.reference)
                    reasons.add(f"EVIDENCE_{item.state.upper()}:{requirement.requirement_id}")
                    continue
                if requirement.maximum_age_seconds is not None:
                    if item.source_as_of is None or utc(item.source_as_of) > at:
                        invalid.add(item.reference)
                        reasons.add(f"INVALID_SOURCE_TIME:{requirement.requirement_id}")
                        continue
                    age = (at - utc(item.source_as_of)).total_seconds()
                    if age > requirement.maximum_age_seconds:
                        stale.add(item.reference)
                        reasons.add(f"STALE_EVIDENCE:{requirement.requirement_id}")
                        continue
                if item.reference in conflicts:
                    reasons.add(f"CONFLICTING_EVIDENCE:{requirement.requirement_id}")
                    continue
                accepted.setdefault(item.checksum, item.reference)
            refs = sorted(accepted.values())
            satisfied = len(refs) >= requirement.minimum_count
            satisfaction[requirement.requirement_id] = refs if satisfied else []
            if not matching:
                missing.append(requirement.requirement_id)
                reasons.add(f"MISSING_EVIDENCE:{requirement.requirement_id}")
            if satisfied:
                earned += requirement.weight
            elif requirement.mandatory:
                mandatory_complete = False
        return EvidenceAssessment(
            contract_version=contract.version,
            snapshot_hash=digest(items),
            required=[r.requirement_id for r in contract.requirements],
            available=sorted({item.reference for item in items if item.state != "unavailable"}),
            missing=sorted(missing),
            stale=sorted(stale),
            invalid=sorted(invalid),
            conflicting=sorted(conflicts),
            satisfaction=satisfaction,
            reasons=sorted(reasons),
            score=(Decimal(earned) / sum(r.weight for r in contract.requirements)).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            ),
            mandatory_complete=mandatory_complete and not conflicts,
        )
