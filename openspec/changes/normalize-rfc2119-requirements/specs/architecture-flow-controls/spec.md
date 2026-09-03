## MODIFIED Requirements

### Requirement: Orchestrator boundary
FRD reference: FR-ARC-001

LangGraph SHALL coordinate workflow state and routing without owning authoritative facts, policy rules or human decisions.

#### Scenario: Workflow capability executes
- GIVEN LangGraph routes to a workflow stage
- WHEN the stage runs
- THEN LangGraph coordinates state and routing
- AND authoritative fact, policy-rule or human-decision ownership remains with the designated capability

#### Scenario: Phase 002 case persistence bypasses orchestration
- **GIVEN** a valid synthetic duplicate-card case create request is accepted during Phase 002
- **WHEN** the case is created, validated, persisted, retrieved, safely replayed, and audited
- **THEN** no LangGraph workflow run or checkpoint is required
- **AND** the durable business record remains available through the Case API

### Requirement: State authority separation
FRD reference: FR-ARC-011

The platform SHALL persist each data class through its designated explicit store and contract.

#### Scenario: Data is persisted
- GIVEN business state, graph state, policy knowledge, transient coordination, files or audit data are written
- WHEN storage ownership is resolved
- THEN each data class uses its designated explicit store/contract

#### Scenario: Phase 002 durable case state uses operational persistence
- **GIVEN** Phase 002 writes case, evidence metadata, provider context, idempotency, timeline, or audit records
- **WHEN** those records are later retrieved
- **THEN** they are read from the operational persistence and audit contracts designated for durable business state
- **AND** Redis is not the durable authority for those records
