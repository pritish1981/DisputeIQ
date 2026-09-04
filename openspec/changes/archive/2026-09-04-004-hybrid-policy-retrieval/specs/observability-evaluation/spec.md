## ADDED Requirements

### Requirement: Policy retrieval regression evaluation
FRD reference: FR-OBS-005, FR-OBS-006, FR-POL-004, FR-POL-005, FR-POL-008

The platform SHALL run retrieval and citation regression evaluations for policy retrieval configuration changes and SHALL record threshold outcomes before a retrieval configuration is accepted for production use.

#### Scenario: Retrieval regression passes
- **GIVEN** a promoted policy corpus and candidate retrieval configuration are available
- **WHEN** the retrieval regression suite runs
- **THEN** duplicate-card retrieval quality, citation correctness, metadata filtering and stale-policy exclusion are evaluated against configured thresholds
- **AND** passing results are recorded with corpus version, index version, retrieval configuration version and correlation ID

#### Scenario: Retrieval regression fails
- **GIVEN** a retrieval configuration fails a mandatory retrieval or citation threshold
- **WHEN** acceptance is requested
- **THEN** the retrieval configuration is not accepted for production use
- **AND** the failed metric, expected threshold and correlation ID are visible in evaluation records

### Requirement: Policy retrieval telemetry
FRD reference: FR-OBS-001, FR-OBS-002, FR-ARC-012

The platform SHALL emit correlated retrieval telemetry that can reconstruct policy resolution latency, candidate counts, result counts, confidence and abstention reason.

#### Scenario: Retrieval telemetry is correlated
- **GIVEN** policy retrieval executes for a case or validation request
- **WHEN** telemetry is recorded
- **THEN** the telemetry includes case ID when available, workflow ID when available, correlation ID, corpus version, index version, retrieval configuration version, eligible candidate count, returned result count and confidence outcome

#### Scenario: Abstention telemetry is correlated
- **GIVEN** policy retrieval abstains because of missing corpus, no candidates, ambiguity, low confidence or missing citations
- **WHEN** telemetry is recorded
- **THEN** the abstention reason is correlated with the policy retrieval request and visible for operational diagnostics
