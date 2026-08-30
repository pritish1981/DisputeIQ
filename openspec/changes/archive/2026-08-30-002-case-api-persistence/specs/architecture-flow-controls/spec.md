## MODIFIED Requirements

### Requirement: Orchestrator boundary
FRD reference: FR-ARC-001

LangGraph SHALL coordinate workflow state and routing without owning authoritative facts, policy rules or human decisions, and Phase 002 Case API persistence SHALL complete without requiring LangGraph execution.

#### Scenario: Workflow capability executes
- **GIVEN** LangGraph routes to a workflow stage
- **WHEN** the stage runs
- **THEN** LangGraph coordinates state and routing
- **AND** authoritative fact, policy-rule or human-decision ownership remains with the designated capability

#### Scenario: Phase 002 case persistence bypasses orchestration
- **GIVEN** a valid synthetic duplicate-card case create request is accepted during Phase 002
- **WHEN** the case is created, validated, persisted, retrieved, safely replayed, and audited
- **THEN** no LangGraph workflow run or checkpoint is required
- **AND** the durable business record remains available through the Case API

### Requirement: State authority separation
FRD reference: FR-ARC-011

The platform SHALL persist each data class through its designated explicit store and contract.

#### Scenario: Data is persisted
- **GIVEN** business state, graph state, policy knowledge, transient coordination, files or audit data are written
- **WHEN** storage ownership is resolved
- **THEN** each data class uses its designated explicit store/contract

#### Scenario: Phase 002 durable case state uses operational persistence
- **GIVEN** Phase 002 writes case, evidence metadata, provider context, idempotency, timeline, or audit records
- **WHEN** those records are later retrieved
- **THEN** they are read from the operational persistence and audit contracts designated for durable business state
- **AND** Redis is not the durable authority for those records

## ADDED Requirements

### Requirement: No autonomous financial execution in Case API
FRD reference: FR-ARC-005, FR-CTX-005

The Phase 002 Case API and synthetic provider contracts SHALL NOT expose autonomous refund, credit, debit, chargeback, settlement-posting, or other material money-movement operations.

#### Scenario: Financial posting unavailable
- **GIVEN** Phase 002 Case API and provider contracts are deployed
- **WHEN** a caller inspects or invokes supported endpoints and provider operations
- **THEN** no autonomous financial posting operation is available
- **AND** synthetic refund or settlement data is read-only investigation context

### Requirement: No LLM authority in Case API persistence
FRD reference: FR-ARC-003, FR-ARC-009

The Phase 002 Case API and persistence layer SHALL NOT depend on LLM, RAG, recommendation, or AI classification behavior to accept, validate, persist, retrieve, replay, or audit a case.

#### Scenario: Case API runs with AI disabled
- **GIVEN** AI-assisted processing is disabled or unavailable
- **WHEN** a valid synthetic duplicate-card case is created, retrieved, safely replayed, and audited
- **THEN** Phase 002 behavior succeeds through deterministic validation and persistence controls
- **AND** no model invocation is required
