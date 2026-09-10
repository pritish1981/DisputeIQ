## ADDED Requirements

### Requirement: Deterministic controls regression gate
FRD reference: FR-RUL-005, FR-OBS-005, FR-CNF-001; UC-E2E-001, UC-EXC-005, UC-EXC-006, UC-EXC-007, UC-EXC-008

The platform SHALL validate versioned evidence contracts, applicability profiles, rule sets and confidence configurations against an independently specified golden suite before activation, including successful, adverse, boundary, missing-data, conflict and failure outcomes.

#### Scenario: Phase 007 acceptance suite passes
- **GIVEN** candidate control versions and a versioned synthetic dataset
- **WHEN** regression and live integration checks run
- **THEN** evidence completeness, SQL policy eligibility, duplicate-card disposition, confidence factors and hard gates match the expected results
- **AND** restart, replay, concurrent/stale resume, version pinning and audit rollback preserve durable authority
- **AND** deterministic services make no model call or financial mutation

#### Scenario: Candidate configuration fails regression
- **GIVEN** any mandatory expected outcome or safety boundary fails
- **WHEN** configuration activation is attempted
- **THEN** activation is blocked and the failed scenario, expected/actual result, dataset and configuration versions are recorded
- **AND** thresholds are not silently changed to turn the failed run into a pass

### Requirement: Correlated control telemetry
FRD reference: FR-OBS-001, FR-OBS-002, FR-ARC-012

The platform SHALL expose control stage latency, outcome, reason codes, exception and gate counts correlated with case/workflow/evaluation IDs and control versions while keeping sensitive raw content out of telemetry.

#### Scenario: Control gate telemetry is visible
- **GIVEN** an evidence, policy, rule or confidence gate executes
- **WHEN** telemetry is recorded
- **THEN** its stage, outcome, safe reasons, version references and correlation fields are available
- **AND** raw documents, provider payloads, credentials and prompts are absent
