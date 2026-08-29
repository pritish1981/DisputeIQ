# Case Intake and Management

## Purpose
Define customer/analyst case intake, validation, lifecycle, idempotency and timeline behavior.

## Requirements

### Requirement: Unique dispute case
FRD reference: FR-CAS-001

The system SHALL create a globally unique case for every accepted dispute.

#### Scenario: Valid dispute creation
- GIVEN an authorized caller submits a valid dispute
- WHEN the create-dispute request is accepted
- THEN a unique immutable case identifier is created
- AND the case is persisted
- AND a CASE_CREATED business audit event is emitted

### Requirement: Mandatory intake validation
FRD reference: FR-CAS-002

The system SHALL validate required intake fields before workflow execution.

#### Scenario: Missing mandatory intake data
- GIVEN required intake data is missing
- WHEN the caller submits the dispute
- THEN graph execution does not begin
- AND structured field-level validation errors are returned

### Requirement: Idempotent mutation
FRD reference: FR-CAS-004

The platform SHALL return the original result without creating a second dispute case when a completed create request is safely replayed with the same idempotency key and logical payload.

#### Scenario: Duplicate create request
- GIVEN a prior request completed successfully with an idempotency key
- WHEN the same logical request is safely replayed with that key
- THEN a second dispute case is not created
- AND the original result is returned
