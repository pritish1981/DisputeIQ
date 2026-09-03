## MODIFIED Requirements

### Requirement: Versioned REST contracts
FRD reference: Section 7.16 API and Integration Requirements

The platform SHALL expose supported public APIs through documented OpenAPI contracts with versioned and validated request and response schemas.

#### Scenario: API contract published
- GIVEN a supported public API exists
- WHEN the service is built
- THEN the contract is documented through OpenAPI
- AND request/response schemas are versioned and validated

#### Scenario: Case API contract published
- **GIVEN** Phase 002 Case API is enabled
- **WHEN** the service publishes OpenAPI
- **THEN** `POST /api/v1/cases`, `GET /api/v1/cases/{case_id}`, `GET /api/v1/cases/{case_id}/timeline`, evidence metadata create/list endpoints, and MVP case listing/search endpoints are documented
- **AND** each request and response uses a Pydantic-backed schema contract

### Requirement: Correlation identifier
FRD reference: FR-ARC-012

The platform SHALL assign an approved correlation identifier to every accepted inbound request and propagate it across downstream workflow operations.

#### Scenario: Request enters platform
- GIVEN an inbound request does not already carry an approved correlation ID
- WHEN the application accepts the request
- THEN a correlation ID is generated
- AND propagated across downstream workflow operations

#### Scenario: Case command carries correlation
- **GIVEN** an inbound case command contains a valid correlation ID
- **WHEN** the command is accepted
- **THEN** the same correlation ID is persisted with case-visible records created by the command
- **AND** returned responses include the correlation ID
