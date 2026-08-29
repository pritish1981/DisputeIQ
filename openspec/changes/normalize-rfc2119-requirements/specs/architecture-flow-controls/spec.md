## MODIFIED Requirements

### Requirement: Orchestrator boundary
FRD reference: FR-ARC-001

LangGraph SHALL coordinate workflow state and routing without owning authoritative facts, policy rules or human decisions.

#### Scenario: Workflow capability executes
- GIVEN LangGraph routes to a workflow stage
- WHEN the stage runs
- THEN LangGraph coordinates state and routing
- AND authoritative fact, policy-rule or human-decision ownership remains with the designated capability

### Requirement: State authority separation
FRD reference: FR-ARC-011

The platform SHALL persist each data class through its designated explicit store and contract.

#### Scenario: Data is persisted
- GIVEN business state, graph state, policy knowledge, transient coordination, files or audit data are written
- WHEN storage ownership is resolved
- THEN each data class uses its designated explicit store/contract
