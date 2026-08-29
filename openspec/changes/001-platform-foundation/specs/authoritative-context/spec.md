## MODIFIED Requirements

### Requirement: Authoritative banking facts
FRD reference: FR-CTX-001, FR-ARC-002

The foundation SHALL capture read-only synthetic banking context for accepted MVP dispute cases using allow-listed mock provider interfaces, and no LLM-generated fact may replace provider data.

#### Scenario: Transaction context retrieval
- **GIVEN** a case contains a valid synthetic transaction reference
- **WHEN** foundation context capture executes during case creation
- **THEN** the transaction provider is invoked through an allow-listed read-only interface
- **AND** provider-returned facts are stored as authoritative synthetic context
- **AND** no LLM-generated fact replaces provider data

## ADDED Requirements

### Requirement: Foundation source lineage
FRD reference: FR-CTX-003

Every captured synthetic provider fact SHALL preserve provider name, source record reference, retrieval timestamp, correlation ID, and response version or hash where feasible.

#### Scenario: Provider context is visible
- **GIVEN** synthetic provider context was captured for a case
- **WHEN** an authorized caller retrieves the case detail
- **THEN** the provider context includes source lineage metadata
- **AND** the lineage can be correlated with the case and audit records
