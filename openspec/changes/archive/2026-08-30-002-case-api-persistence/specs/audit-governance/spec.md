## MODIFIED Requirements

### Requirement: Immutable material events
FRD reference: FR-AUD-001

The platform SHALL record every material case lifecycle action as an append-only business audit event independent of application logs.

#### Scenario: Material lifecycle action occurs
- **GIVEN** a material case lifecycle action completes
- **WHEN** audit recording executes
- **THEN** an append-only business audit event is written independently of application logs

#### Scenario: Phase 002 audit failure blocks accepted mutation
- **GIVEN** a material Phase 002 case mutation requires an audit event
- **WHEN** the audit event cannot be persisted in the same accepted operation boundary
- **THEN** the mutation is not reported as successful
- **AND** no accepted case or evidence metadata mutation is left without its required business audit event

## ADDED Requirements

### Requirement: Baseline audit event contract
FRD reference: FR-AUD-002

Phase 002 business audit events SHALL include event ID, case ID, actor, timestamp, event type, source, correlation ID, relevant version metadata, and object references needed for case reconstruction.

#### Scenario: Case creation audit event
- **GIVEN** a synthetic duplicate-card case is created
- **WHEN** the `CASE_CREATED` event is persisted
- **THEN** the audit event includes event ID, case ID, actor, timestamp, event type, source, correlation ID, state version, and relevant request/provider metadata references

#### Scenario: Evidence metadata audit event
- **GIVEN** evidence metadata is registered for a case
- **WHEN** the material evidence event is persisted
- **THEN** the audit event includes event ID, case ID, evidence ID or object reference, actor, timestamp, event type, source, correlation ID, and state version

### Requirement: Audit-linked replay visibility
FRD reference: FR-CAS-004, FR-AUD-001, FR-AUD-002

The platform SHALL make safe idempotent replays observable without duplicating material business audit events.

#### Scenario: Idempotent replay does not duplicate material event
- **GIVEN** a create-case request has already emitted `CASE_CREATED`
- **WHEN** the same logical request is replayed with the same idempotency key
- **THEN** the original case result is returned
- **AND** no second `CASE_CREATED` audit event is emitted
- **AND** replay metadata is available for operational diagnostics
