## ADDED Requirements

### Requirement: Workflow API contracts
FRD reference: API / integration requirements, FR-WFL-001, FR-WFL-005, FR-ARC-012

The platform SHALL expose versioned workflow APIs for starting, inspecting and resuming case workflows with validated request and response schemas, idempotency, optimistic state-version checks and correlation identifiers.

#### Scenario: Start workflow API
- **GIVEN** an authorized caller submits a valid workflow start command for an existing case
- **WHEN** the command is accepted
- **THEN** the response includes case ID, workflow ID, status, current node, state version, graph version, correlation ID and latest checkpoint metadata
- **AND** the accepted response is safely replayable with the same idempotency key and payload

#### Scenario: Inspect workflow API
- **GIVEN** a workflow run exists
- **WHEN** an authorized caller retrieves workflow detail
- **THEN** the response includes run status, current node, state version, checkpoint sequence, interrupt metadata, stage summaries, error metadata and correlation ID

#### Scenario: Resume workflow API
- **GIVEN** an interrupted workflow has a valid checkpoint
- **WHEN** an authorized caller submits a valid resume command with idempotency key and matching state version
- **THEN** the response includes the resumed workflow status, next state version, current node, correlation ID and checkpoint metadata

### Requirement: Workflow API errors
FRD reference: API / integration requirements, FR-WFL-005, FR-OBS-001

The platform SHALL return structured workflow API errors with stable error code, human-readable message, correlation ID and field-level details where applicable.

#### Scenario: Workflow conflict response
- **GIVEN** a workflow start or resume command conflicts with current workflow state or state version
- **WHEN** the command is rejected
- **THEN** the response uses a stable conflict error code and includes the correlation ID
- **AND** no workflow state mutation is accepted
