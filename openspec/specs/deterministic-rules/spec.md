# Deterministic Rules and Validation

## Purpose
Define authoritative deterministic eligibility, timeline, evidence and dispute decision rules.

## Requirements

### Requirement: Core rules execute outside LLM
FRD reference: FR-RUL-001, FR-ARC-005

The deterministic Rules Engine SHALL own authoritative core rule outcomes, and the platform SHALL NOT treat LLM output as an authoritative rule result.

#### Scenario: Rules evaluated
- GIVEN authoritative context, evidence assessment and applicable policy metadata
- WHEN decision rules execute
- THEN the deterministic Rules Engine returns rule outcomes
- AND no LLM output is treated as the authoritative rule result

### Requirement: Versioned rule result
FRD reference: FR-RUL-002

The platform SHALL retain the rule ID, version, outcome, reason and policy or configuration reference for every configured rule result.

#### Scenario: Rule result is recorded
- GIVEN a configured rule executes
- WHEN a result is produced
- THEN rule ID, version, outcome, reason and policy/configuration reference are retained
