## MODIFIED Requirements

### Requirement: Versioned REST contracts
FRD reference: Section 7.16 API and Integration Requirements

The system SHALL expose versioned REST contracts for foundation case creation and retrieval, with request and response schemas documented through OpenAPI.

#### Scenario: API contract published
- **GIVEN** the foundation case API exists
- **WHEN** the service is built
- **THEN** the create-case and retrieve-case contracts are documented through OpenAPI
- **AND** request and response schemas are versioned and validated

### Requirement: Correlation identifier
FRD reference: FR-ARC-012

The system SHALL accept or generate a correlation ID for inbound foundation API requests and propagate it to persisted case, timeline, provider-context, and audit records created during the request.

#### Scenario: Request enters platform
- **GIVEN** an inbound create-case request does not already carry an approved correlation ID
- **WHEN** the application accepts the request
- **THEN** a correlation ID is generated
- **AND** the correlation ID is returned to the caller
- **AND** the correlation ID is propagated to downstream foundation records

#### Scenario: Request enters platform with correlation ID
- **GIVEN** an inbound create-case request carries an approved correlation ID
- **WHEN** the application accepts the request
- **THEN** the supplied correlation ID is retained
- **AND** the correlation ID is propagated to downstream foundation records
