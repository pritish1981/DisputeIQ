## MODIFIED Requirements

### Requirement: Immutable material events
FRD reference: FR-AUD-001

The platform SHALL record every material case lifecycle action as an append-only business audit event independent of application logs.

#### Scenario: Material lifecycle action occurs
- GIVEN a material case lifecycle action completes
- WHEN audit recording executes
- THEN an append-only business audit event is written independently of application logs

#### Scenario: Phase 002 audit failure blocks accepted mutation
- **GIVEN** a material Phase 002 case mutation requires an audit event
- **WHEN** the audit event cannot be persisted in the same accepted operation boundary
- **THEN** the mutation is not reported as successful
- **AND** no accepted case or evidence metadata mutation is left without its required business audit event

### Requirement: Decision reconstruction
FRD reference: FR-AUD-003, FR-AUD-004

The platform SHALL retain sufficient evidence, policy, rule, AI configuration, recommendation and human-decision lineage to reconstruct a completed case.

#### Scenario: Auditor reconstructs completed case
- GIVEN an authorized auditor selects a closed case
- WHEN the audit view is reconstructed
- THEN evidence, policy, rules, AI configuration, recommendation and human decision are traceable
