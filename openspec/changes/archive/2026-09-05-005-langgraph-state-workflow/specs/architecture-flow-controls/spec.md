## ADDED Requirements

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
