## ADDED Requirements

### Requirement: Phase 005 checkpoint persistence
FRD reference: FR-WFL-001, FR-WFL-002, FR-ARC-011

The platform SHALL persist Phase 005 workflow runs and checkpoints in PostgreSQL through a logical checkpoint contract separate from case business state, policy knowledge, Redis and immutable audit events.

#### Scenario: Checkpoint store is separate
- **GIVEN** a workflow run reaches a node boundary or interrupt
- **WHEN** the checkpoint is saved
- **THEN** workflow run metadata and checkpoint state are persisted through the workflow checkpoint contract
- **AND** Redis is not the sole durable authority
- **AND** case business-state records remain owned by the Case Service contract

#### Scenario: Checkpoint can reconstruct workflow position
- **GIVEN** an authorized caller inspects a workflow run
- **WHEN** the latest checkpoint exists
- **THEN** the response identifies current node, status, checkpoint sequence, state version, interrupt reason and stage summary needed for operational recovery

### Requirement: Resume side-effect safety
FRD reference: FR-WFL-005, FR-CTX-004, FR-ARC-011

The platform SHALL record completed node side effects and SHALL NOT duplicate completed external side effects when workflow execution is retried or resumed.

#### Scenario: Completed node is not duplicated
- **GIVEN** a workflow checkpoint records that a provider, policy retrieval or audit side effect has completed
- **WHEN** the workflow resumes from that checkpoint
- **THEN** the completed side effect is not executed again
- **AND** the workflow continues from the next safe boundary

#### Scenario: Idempotent replay returns accepted workflow result
- **GIVEN** a workflow start or resume command has already been accepted for the same idempotency key and payload
- **WHEN** the same logical command is replayed
- **THEN** the previously accepted workflow response is returned
- **AND** no second workflow run, checkpoint or material audit event is emitted

### Requirement: Workflow error classification
FRD reference: FR-WFL-003, FR-WFL-004, FR-CTX-004

The platform SHALL classify workflow execution failures as retriable, manual-degradation, validation or fatal failures and SHALL expose the classification in checkpoint, API and telemetry records.

#### Scenario: Retriable dependency failure
- **GIVEN** a bounded provider or policy retrieval dependency fails with a retriable timeout or transient error
- **WHEN** the workflow handles the failure
- **THEN** retry metadata is recorded in workflow state
- **AND** retries stop at the configured limit before manual degradation is signaled

#### Scenario: Manual degradation failure
- **GIVEN** an LLM, RAG or non-critical tool capability required by the current stage is unavailable after allowed retries
- **WHEN** workflow recovery evaluates the failure
- **THEN** the workflow is checkpointed into a controlled manual-processing status
- **AND** the response includes the manual-degradation reason
