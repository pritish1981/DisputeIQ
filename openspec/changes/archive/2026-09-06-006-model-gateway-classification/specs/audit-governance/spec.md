## ADDED Requirements

### Requirement: Model Gateway and classification audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-AIP-003, FR-CLS-004

The platform SHALL record Model Gateway invocations, classification outcomes, schema validation failures, kill-switch bypasses and manual-classification routing as audit-visible lineage sufficient to reconstruct AI-assisted classification behavior.

#### Scenario: Classification success is audited
- **GIVEN** AI-assisted classification succeeds with a supported category
- **WHEN** the result is accepted
- **THEN** audit-visible lineage records case ID, workflow ID when available, actor or service, event type, source, correlation ID, category, confidence, model route version, prompt version, schema version, token usage and timestamp
- **AND** raw provider payloads and hidden reasoning are not required for business audit reconstruction

#### Scenario: Classification fallback is audited
- **GIVEN** classification is bypassed, retried, falls back, fails schema validation, returns low confidence or identifies an unsupported category
- **WHEN** automated progression is paused
- **THEN** audit-visible lineage records the failure or bypass reason, attempt count, fallback outcome, configured threshold, manual-classification signal and correlation ID

#### Scenario: Audit failure blocks accepted AI transition
- **GIVEN** a classification transition requires audit-visible lineage
- **WHEN** the lineage event cannot be persisted in the accepted operation boundary
- **THEN** the classification transition is not reported as successful
- **AND** no automated continuation signal is emitted without required lineage
