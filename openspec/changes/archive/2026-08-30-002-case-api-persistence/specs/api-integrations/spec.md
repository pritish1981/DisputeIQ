## MODIFIED Requirements

### Requirement: Versioned REST contracts
FRD reference: Section 7.16 API and Integration Requirements, FR-CAS-001, FR-CAS-004, FR-CAS-005, FR-EVD-001

The platform SHALL expose supported public APIs through documented OpenAPI contracts with versioned and validated request and response schemas.

#### Scenario: API contract published
- **GIVEN** a supported public API exists
- **WHEN** the service is built
- **THEN** the contract is documented through OpenAPI
- **AND** request/response schemas are versioned and validated

#### Scenario: Case API contract published
- **GIVEN** Phase 002 Case API is enabled
- **WHEN** the service publishes OpenAPI
- **THEN** `POST /api/v1/cases`, `GET /api/v1/cases/{case_id}`, `GET /api/v1/cases/{case_id}/timeline`, evidence metadata create/list endpoints, and MVP case listing/search endpoints are documented
- **AND** each request and response uses a Pydantic-backed schema contract

### Requirement: Correlation identifier
FRD reference: FR-ARC-012, FR-AUD-002

The platform SHALL assign an approved correlation identifier to every accepted inbound request and propagate it across downstream case, provider-context, timeline, and audit records.

#### Scenario: Request enters platform
- **GIVEN** an inbound request does not already carry an approved correlation ID
- **WHEN** the application accepts the request
- **THEN** a correlation ID is generated
- **AND** propagated across downstream workflow operations

#### Scenario: Case command carries correlation
- **GIVEN** an inbound case command contains a valid correlation ID
- **WHEN** the command is accepted
- **THEN** the same correlation ID is persisted with case-visible records created by the command
- **AND** returned responses include the correlation ID

## ADDED Requirements

### Requirement: Case command controls
FRD reference: FR-CAS-002, FR-CAS-004

Mutating Case API endpoints SHALL require idempotency keys and SHALL return structured machine-readable errors for validation, idempotency conflict, not-found, unauthorized, and optimistic-lock conflict cases.

#### Scenario: Missing idempotency key
- **GIVEN** a caller submits a mutating case command without an idempotency key
- **WHEN** the request is validated
- **THEN** the request is rejected before persistence
- **AND** the error response identifies the missing control

#### Scenario: Structured API error
- **GIVEN** a Case API request fails validation or control checks
- **WHEN** the error response is returned
- **THEN** it contains a stable error code, human-readable message, correlation ID, and field-level details where applicable

### Requirement: Synthetic provider contracts
FRD reference: FR-CTX-001, FR-CTX-002, FR-CTX-003, FR-CTX-005

The platform SHALL define stable contracts for synthetic `TransactionProvider`, `CustomerProvider`, `AccountProvider`, `MerchantProvider`, `SettlementProvider`, and `RefundProvider` test doubles used by Phase 002 case validation and context persistence.

#### Scenario: Provider contract returns stable DTO
- **GIVEN** a Phase 002 synthetic provider is invoked for an allow-listed read operation
- **WHEN** the provider returns data
- **THEN** the response uses a stable DTO with provider name, source record reference, retrieval timestamp, source version or response hash, and normalized facts required by the case API

#### Scenario: Provider contract denies posting action
- **GIVEN** Phase 002 provider contracts are available
- **WHEN** a caller or service attempts refund, credit, debit, settlement posting, or other financial mutation through these contracts
- **THEN** the action is unavailable or denied
- **AND** no financial side effect occurs
