## MODIFIED Requirements

### Requirement: Immutable material events
FRD reference: FR-AUD-001

The system SHALL write append-only business audit events for foundation material lifecycle actions independently of application logs.

#### Scenario: Material lifecycle action occurs
- **GIVEN** a synthetic dispute case is created
- **WHEN** audit recording executes
- **THEN** an append-only `CASE_CREATED` business audit event is written independently of application logs
- **AND** the event is linked to the case ID and correlation ID

## ADDED Requirements

### Requirement: Foundation audit event contract
FRD reference: FR-AUD-002

Foundation audit events SHALL include audit event ID, timestamp, case ID, event type, actor, source, correlation ID, and relevant before/after or object reference metadata when available.

#### Scenario: Audit event is persisted
- **GIVEN** a foundation audit event is emitted
- **WHEN** the event is stored
- **THEN** the stored event contains the required audit contract fields
- **AND** the event can be retrieved with the associated case detail for audit visibility
