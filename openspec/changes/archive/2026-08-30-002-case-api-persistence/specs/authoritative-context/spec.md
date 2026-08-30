## MODIFIED Requirements

### Requirement: Authoritative banking facts
FRD reference: FR-CTX-001, FR-ARC-002

The platform SHALL obtain banking facts from designated allow-listed providers and SHALL NOT replace provider data with LLM-generated facts.

#### Scenario: Transaction context retrieval
- **GIVEN** a case contains a valid transaction reference
- **WHEN** the authoritative-context stage executes
- **THEN** the transaction provider is invoked
- **AND** provider-returned facts are stored as authoritative context
- **AND** no LLM-generated fact replaces provider data

#### Scenario: Phase 002 synthetic context capture
- **GIVEN** a valid synthetic duplicate-card case contains customer and transaction references
- **WHEN** the case is created or validated in Phase 002
- **THEN** allow-listed synthetic providers return transaction, customer, account, merchant, settlement, and refund context where configured for the fixture
- **AND** returned context is persisted with source lineage for retrieval and audit
- **AND** no LLM-generated fact is used as authoritative context

### Requirement: Tool authorization
FRD reference: FR-CTX-005

The platform SHALL deny and audit any workflow tool invocation outside the invoking node's allow-list.

#### Scenario: Disallowed tool request
- **GIVEN** a workflow node attempts to invoke a tool outside its allow-list
- **WHEN** tool authorization evaluates the call
- **THEN** the call is denied
- **AND** the violation is audited

#### Scenario: Disallowed Phase 002 provider operation
- **GIVEN** Phase 002 executes without LangGraph runtime orchestration
- **WHEN** a service attempts a provider operation outside the Phase 002 read-only allow-list
- **THEN** the operation is denied or unavailable
- **AND** the denial is observable through structured error and audit metadata where the request is material

## ADDED Requirements

### Requirement: Related synthetic context
FRD reference: FR-CTX-002

The platform SHALL retrieve and persist related synthetic banking context needed for duplicate-card case validation without treating that context as a financial posting instruction.

#### Scenario: Related context returned
- **GIVEN** a synthetic duplicate-card fixture has related account, merchant, settlement, or refund records
- **WHEN** the platform resolves authoritative context for the case
- **THEN** the related records are associated with the case
- **AND** the case response exposes normalized references and lineage needed for investigation

### Requirement: Provider source lineage
FRD reference: FR-CTX-003

The platform SHALL retain source lineage for every authoritative provider fact persisted during Phase 002.

#### Scenario: Context lineage persisted
- **GIVEN** a synthetic provider returns an authoritative fact
- **WHEN** the fact is persisted for a case
- **THEN** the persisted context includes provider name, source record reference, retrieval timestamp, correlation ID, and source version or response hash
