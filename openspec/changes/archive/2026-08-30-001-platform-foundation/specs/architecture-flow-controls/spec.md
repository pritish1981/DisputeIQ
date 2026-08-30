## MODIFIED Requirements

### Requirement: State authority separation
FRD reference: FR-ARC-011

Foundation business state, synthetic provider context references, evidence metadata, idempotency records, and audit events SHALL use explicit persistence contracts; Redis SHALL NOT be used as durable authority for these records.

#### Scenario: Data is persisted
- **GIVEN** foundation case, provider-context, evidence metadata, idempotency, or audit data are written
- **WHEN** storage ownership is resolved
- **THEN** each data class uses its designated explicit store or contract
- **AND** Redis is not the durable source of truth for foundation business records

## ADDED Requirements

### Requirement: Foundation excludes autonomous financial execution
FRD reference: FR-ARC-008, FR-ARC-009, FR-ARC-010

The platform foundation SHALL NOT expose any autonomous refund, credit, debit, chargeback, or material financial posting capability.

#### Scenario: Foundation tool surface is inspected
- **GIVEN** the foundation service is deployed
- **WHEN** available foundation APIs and provider interfaces are inspected
- **THEN** no API or provider interface can post a refund, credit, debit, chargeback, or other material financial outcome

### Requirement: Foundation excludes AI and workflow execution
FRD reference: FR-ARC-001, FR-ARC-007

The platform foundation SHALL NOT execute LangGraph workflow nodes or invoke LLM providers before the corresponding later OpenSpec changes are approved.

#### Scenario: Case is created during foundation phase
- **GIVEN** a valid synthetic dispute is accepted during the foundation phase
- **WHEN** the case is created
- **THEN** no LangGraph workflow execution begins
- **AND** no LLM or Model Gateway invocation occurs
