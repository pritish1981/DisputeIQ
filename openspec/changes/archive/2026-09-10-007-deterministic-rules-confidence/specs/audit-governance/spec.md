## ADDED Requirements

### Requirement: Deterministic control audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-RUL-003

The platform SHALL emit append-only correlated events for control configuration registration, evidence assessment, policy eligibility, rule execution, confidence evaluation, review requests and explicit re-evaluation, retaining actor, time, case/workflow/evaluation IDs and consumed version/hash references.

#### Scenario: Control result is reconstructed
- **GIVEN** an accepted deterministic evaluation
- **WHEN** its audit lineage is inspected
- **THEN** the original facts/evidence references, evaluation time, policy citations, rule set, formula, thresholds, reasons and outputs are traceable
- **AND** deterministic findings are distinguishable from AI outputs and any later human decision

#### Scenario: Audit write failure prevents acceptance
- **GIVEN** a material control result or review request requires an audit event
- **WHEN** audit persistence fails
- **THEN** the corresponding transition is rolled back and not reported as successful

#### Scenario: Re-evaluation preserves previous lineage
- **GIVEN** an authorized re-evaluation of changed inputs or versions
- **WHEN** its event is recorded
- **THEN** the reason and prior/new evaluation references are retained
- **AND** prior records are not rewritten and an identical retry does not duplicate material events
