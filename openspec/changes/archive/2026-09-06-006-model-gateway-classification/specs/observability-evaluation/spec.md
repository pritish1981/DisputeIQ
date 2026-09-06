## ADDED Requirements

### Requirement: Model Gateway and classification telemetry
FRD reference: FR-OBS-001, FR-OBS-002, FR-OBS-005, FR-OBS-006, FR-ARC-012

The platform SHALL emit correlated telemetry for Model Gateway requests and classification outcomes, including latency, token usage, provider route, prompt version, schema version, retries, fallback, kill-switch status and confidence gate outcome.

#### Scenario: Classification telemetry is correlated
- **GIVEN** classification executes for a case workflow
- **WHEN** telemetry is recorded
- **THEN** it includes case ID, workflow ID when available, correlation ID, capability name, model route version, prompt version, schema version, provider route reference, latency, token usage, status and confidence outcome

#### Scenario: Gateway failure telemetry is correlated
- **GIVEN** model execution is bypassed, times out, falls back or fails validation
- **WHEN** telemetry is recorded
- **THEN** the reason, attempt count, fallback outcome, kill-switch state when relevant, and manual-routing outcome are visible for operational diagnostics

### Requirement: Classification validation suite
FRD reference: FR-CLS-001, FR-CLS-002, FR-CLS-003, FR-CLS-004, FR-AIP-004, FR-OBS-005, FR-OBS-006

The platform SHALL include automated validation proving classification schema conformance, supported-category routing, unsupported-category handling, confidence gates, kill-switch bypass, fallback behavior, audit lineage, telemetry correlation and direct-provider-call prohibition.

#### Scenario: Phase 006 validation passes
- **GIVEN** Phase 006 implementation is complete
- **WHEN** the validation suite runs
- **THEN** tests prove duplicate-card, failed-UPI and ATM debit-without-cash classification outputs conform to the versioned schema
- **AND** low-confidence, malformed, unsupported, kill-switch and provider-failure cases route to manual classification
- **AND** no direct provider SDK call, recommendation, customer communication or financial posting capability is required for the validation path

#### Scenario: Classification configuration regression fails
- **GIVEN** a candidate model route, prompt, schema or threshold configuration fails mandatory classification metrics
- **WHEN** acceptance is requested
- **THEN** the configuration is not accepted for production use
- **AND** failed metric, expected threshold and correlation ID are visible in evaluation records
