## MODIFIED Requirements

### Requirement: Unique dispute case
FRD reference: FR-CAS-001

The system SHALL create a globally unique case for every accepted synthetic MVP dispute with customer reference, transaction reference, channel, submitted timestamp, dispute description, dispute type when supplied, and lifecycle status.

#### Scenario: Valid dispute creation
- **GIVEN** an authorized caller submits a valid synthetic duplicate-card dispute with required intake fields and an idempotency key
- **WHEN** the create-dispute request is accepted
- **THEN** a unique immutable case identifier is created
- **AND** the case is persisted with status `Submitted`
- **AND** the accepted response includes the case identifier, status, correlation ID, and created timestamp
- **AND** a `CASE_CREATED` business audit event is emitted

### Requirement: Mandatory intake validation
FRD reference: FR-CAS-002

The system SHALL validate configured mandatory intake fields before any workflow or AI-assisted processing begins.

#### Scenario: Missing mandatory intake data
- **GIVEN** required intake data is missing
- **WHEN** the caller submits the dispute
- **THEN** graph execution does not begin
- **AND** no AI-assisted processing begins
- **AND** structured field-level validation errors are returned
- **AND** no dispute case is created

### Requirement: Idempotent mutation
FRD reference: FR-CAS-004

Mutating case APIs SHALL accept an idempotency key and return the original result for safe replay of the same logical request.

#### Scenario: Duplicate create request
- **GIVEN** a prior create-dispute request completed successfully with an idempotency key and matching request fingerprint
- **WHEN** the same logical request is safely replayed with that key
- **THEN** a second dispute case is not created
- **AND** the original result is returned
- **AND** the replay is traceable through the original case and correlation metadata

#### Scenario: Idempotency key reused for different payload
- **GIVEN** a prior create-dispute request completed with an idempotency key
- **WHEN** a different logical request is submitted using the same idempotency key
- **THEN** the request is rejected as an idempotency conflict
- **AND** no second dispute case is created

## ADDED Requirements

### Requirement: Foundation case lifecycle
FRD reference: FR-CAS-003

The foundation SHALL support the initial case lifecycle states needed before workflow orchestration is introduced: `Draft`, `Submitted`, `Manual Processing`, and `Closed`.

#### Scenario: Case is accepted into submitted state
- **GIVEN** a valid synthetic dispute intake request is accepted
- **WHEN** the case record is created
- **THEN** the case lifecycle status is `Submitted`
- **AND** later workflow-specific statuses are not required by this foundation change

### Requirement: Case timeline visibility
FRD reference: FR-CAS-005

The system SHALL expose a chronological case timeline containing foundation case and audit-relevant events.

#### Scenario: Case detail includes timeline
- **GIVEN** a synthetic dispute case was created
- **WHEN** an authorized caller retrieves the case detail
- **THEN** the response includes timeline entries in chronological order
- **AND** the creation timeline entry is correlated to the `CASE_CREATED` audit event
