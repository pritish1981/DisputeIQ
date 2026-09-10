## ADDED Requirements

### Requirement: Versioned evidence contract evaluation
FRD reference: FR-EVD-002, FR-EVD-003, FR-ARC-003

The platform SHALL evaluate a pinned evidence contract selected by dispute type, channel and policy/rule context, returning required, available, missing, stale, invalid and conflicting evidence, per-requirement reasons, completeness score and a separate mandatory-completeness gate.

#### Scenario: Configured evidence is satisfied
- **GIVEN** a valid pinned contract and qualifying evidence with authoritative lineage
- **WHEN** completeness is evaluated at the pinned time
- **THEN** required items and satisfying evidence references are returned with contract version and snapshot hash
- **AND** the completeness score follows the contract weights and mandatory status reflects every mandatory requirement

#### Scenario: Unrelated or duplicate upload cannot satisfy the gate
- **GIVEN** mandatory transaction evidence is absent but unrelated or duplicate uploads exist
- **WHEN** completeness is evaluated
- **THEN** the missing requirement remains unsatisfied
- **AND** duplicate evidence cannot inflate its weight or bypass mandatory completeness

#### Scenario: Invalid or unavailable contract fails closed
- **GIVEN** no unique approved contract exists or its denominator is empty or invalid
- **WHEN** evaluation is attempted
- **THEN** a configuration-review reason is returned without a successful completeness score
- **AND** automated progression is blocked

### Requirement: Evidence freshness and conflict reasons
FRD reference: FR-EVD-003, FR-EVD-005, FR-ARC-003

The platform SHALL apply configured freshness, validity and conflict predicates to evidence and authoritative facts at a pinned evaluation time, retain provenance for each finding, and SHALL NOT use an LLM to silently resolve authoritative conflicts.

#### Scenario: Evidence becomes stale under the contract
- **GIVEN** evidence is older than its configured maximum age relative to evaluation time
- **WHEN** the evidence requirement is evaluated
- **THEN** the item appears as stale and cannot satisfy that requirement
- **AND** exact equality at the configured maximum age remains fresh

#### Scenario: Conflicting authoritative evidence blocks readiness
- **GIVEN** authoritative records contain an unresolved blocking ownership, identity, currency or status conflict
- **WHEN** assessment runs
- **THEN** both conflicting references and a deterministic reason are retained
- **AND** readiness is blocked for rule or human review without silently selecting a convenient value

#### Scenario: Unverified evidence is distinct from missing evidence
- **GIVEN** registered evidence has unavailable validation, inaccessible content or extraction failure
- **WHEN** assessment runs
- **THEN** it remains visible as present but invalid or unverifiable as appropriate
- **AND** it is neither marked absent solely for extraction failure nor accepted as validated evidence

### Requirement: Durable evidence request and reassessment
FRD reference: FR-EVD-004, FR-WFL-005

The platform SHALL persist an evidence request identifying unsatisfied mandatory requirements with the blocked checkpoint, and SHALL reassess registered evidence before authorized resume can progress.

#### Scenario: Missing evidence creates one request
- **GIVEN** mandatory evidence is missing, stale or invalid
- **WHEN** the gate executes or is retried for the same evaluation
- **THEN** one durable evidence request is associated with that evaluation and the workflow waits for evidence
- **AND** downstream policy, rules and confidence readiness cannot proceed

#### Scenario: New evidence is evaluated before continuation
- **GIVEN** an evidence request and newly registered qualifying evidence
- **WHEN** an authorized caller resumes with the current workflow version
- **THEN** a linked reassessment preserves the original result and request lineage
- **AND** progression occurs only if the updated mandatory gate passes
