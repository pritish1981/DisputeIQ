# Architecture and Flow Controls

## Purpose
Define cross-cutting architecture constraints that every OpenSpec change must preserve.

## Requirements

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

### Requirement: Step 5 controlled policy resolution boundary
FRD reference: FR-ARC-004, FR-POL-003, FR-POL-004, FR-POL-006

The platform SHALL keep Step 5 policy resolution as a controlled retrieval boundary where deterministic eligibility executes before retrieval and low-confidence outcomes route to policy review.

#### Scenario: Eligibility precedes retrieval in Step 5
- **GIVEN** policy context is required for a dispute
- **WHEN** Step 5 policy resolution begins
- **THEN** deterministic applicability filters execute before lexical, vector or reranking operations
- **AND** retrieval cannot include chunks excluded by status, effective date, product, channel, jurisdiction or configured applicability metadata

#### Scenario: Policy resolution does not decide material outcome
- **GIVEN** policy retrieval returns applicable cited context
- **WHEN** Step 5 policy resolution completes
- **THEN** the result contains policy context, citations and confidence signals only
- **AND** no material financial outcome, recommendation, customer communication or posting operation is executed by policy retrieval

#### Scenario: Low-confidence policy resolution routes to policy review
- **GIVEN** policy retrieval is missing, ambiguous, uncited or below threshold
- **WHEN** Step 5 policy resolution completes
- **THEN** automated continuation is stopped with a policy-review HITL signal
- **AND** later workflow stages cannot treat the missing policy context as approved policy authority

### Requirement: Phase 005 orchestration boundary
FRD reference: FR-ARC-001, FR-ARC-002, FR-ARC-003, FR-ARC-004, FR-ARC-005, FR-ARC-008, FR-ARC-011

The Phase 005 workflow SHALL make LangGraph responsible for routing, checkpoints, interrupts and resumes, while authoritative facts, evidence completeness, policy eligibility/retrieval, deterministic rules, human decisions and financial outcomes remain owned by their designated capabilities.

#### Scenario: LangGraph routes without taking authority
- **GIVEN** a workflow node needs authoritative context, policy context or deterministic gate output
- **WHEN** the node executes
- **THEN** LangGraph invokes the designated bounded service or adapter
- **AND** the returned service result is recorded as the node output
- **AND** LangGraph does not replace provider facts, policy applicability, rule outcomes or human decisions with autonomous reasoning

#### Scenario: Financial operations remain unavailable
- **GIVEN** Phase 005 workflow APIs, nodes and adapters are deployed
- **WHEN** supported endpoints, node tool allow-lists and provider operations are inspected
- **THEN** no refund, credit, debit, chargeback, settlement-posting or material money-movement operation is available
- **AND** workflow completion cannot record a final material financial outcome without a later approved human-decision capability

### Requirement: Node tool allow-list enforcement
FRD reference: FR-CTX-005, FR-SEC-006, FR-ARC-002

Each workflow node SHALL execute only explicitly allow-listed service/tool operations and SHALL fail closed with audit-visible metadata when a disallowed operation is requested.

#### Scenario: Disallowed node tool is denied
- **GIVEN** a workflow node attempts to call a service or adapter outside its allow-list
- **WHEN** tool authorization evaluates the call
- **THEN** the call is denied before execution
- **AND** the violation is recorded with workflow ID, node name, correlation ID and actor/service identity
