# API and Integrations

## Purpose
Define public application interfaces and provider contracts.

## Requirements

### Requirement: Versioned REST contracts
FRD reference: Section 7.16 API and Integration Requirements

The platform SHALL expose supported public APIs through documented OpenAPI contracts with versioned and validated request and response schemas.

#### Scenario: API contract published
- GIVEN a supported public API exists
- WHEN the service is built
- THEN the contract is documented through OpenAPI
- AND request/response schemas are versioned and validated

### Requirement: Correlation identifier
FRD reference: FR-ARC-012

The platform SHALL assign an approved correlation identifier to every accepted inbound request and propagate it across downstream workflow operations.

#### Scenario: Request enters platform
- GIVEN an inbound request does not already carry an approved correlation ID
- WHEN the application accepts the request
- THEN a correlation ID is generated
- AND propagated across downstream workflow operations
