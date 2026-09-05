# workflow-orchestration Specification

## Purpose
Define the Phase 005 LangGraph orchestration runtime for starting, checkpointing, interrupting, resuming and inspecting governed dispute workflows.

## Requirements

### Requirement: Workflow start contract
FRD reference: FR-WFL-001, FR-WFL-002, FR-ARC-001, FR-ARC-012

The platform SHALL start a workflow only for an existing submitted case through an explicit workflow command, and SHALL assign a workflow ID, graph version, state version and correlation ID before any graph node executes.

#### Scenario: Submitted case workflow starts
- **GIVEN** an existing submitted duplicate-card case has no active workflow
- **WHEN** an authorized caller starts the investigation workflow
- **THEN** a workflow run is created with status `RUNNING`
- **AND** the initial workflow state includes case ID, workflow ID, graph version, state version and correlation ID
- **AND** Phase 002 case creation remains available without implicitly starting LangGraph

#### Scenario: Unknown or unsupported case is rejected
- **GIVEN** the requested case does not exist or is not eligible for Phase 005 orchestration
- **WHEN** workflow start is requested
- **THEN** the request is rejected with a structured error and correlation ID
- **AND** no workflow run or checkpoint is created

### Requirement: Typed workflow state envelope
FRD reference: FR-WFL-001, FR-WFL-002, FR-ARC-011

The platform SHALL persist a compact typed workflow state envelope that stores identifiers, node outputs, interrupt metadata, retry/error metadata, state version and references to external records without copying full authoritative provider records or evidence binaries into checkpoint state.

#### Scenario: Workflow state is checkpointed
- **GIVEN** a workflow node reaches a material boundary
- **WHEN** workflow state is persisted
- **THEN** the checkpoint contains compact stage outputs, external record references, control metadata and state version
- **AND** large evidence content, provider payloads, secrets and tokens are absent from workflow state

#### Scenario: State ownership is constrained
- **GIVEN** a workflow node writes a stage result
- **WHEN** the state update is accepted
- **THEN** only the node's declared state slice and control/error metadata are changed
- **AND** previously approved human decision state cannot be overwritten by automated nodes

### Requirement: Governed graph progression
FRD reference: FR-ARC-001, FR-ARC-002, FR-ARC-003, FR-ARC-004, FR-ARC-005, FR-ARC-008

The platform SHALL use LangGraph to coordinate routing across bounded workflow stages while designated provider, deterministic, policy, model-gateway and human capabilities retain authority for their owned decisions and data.

#### Scenario: Duplicate-card workflow progresses through available stages
- **GIVEN** a submitted duplicate-card case has persisted authoritative context and a promoted applicable policy corpus
- **WHEN** Phase 005 workflow execution runs
- **THEN** LangGraph routes through intake, classification routing, authoritative-context reference capture, evidence gate and policy-context resolution
- **AND** the resulting workflow state records stage outcomes, citations or interrupt signals without finalizing a material financial outcome

#### Scenario: Later capability boundary stops progression
- **GIVEN** the workflow reaches recommendation, durable human decision, communication or financial finalization behavior that is outside Phase 005
- **WHEN** routing evaluates the next stage
- **THEN** automated progression stops with a controlled workflow status and reason
- **AND** no recommendation, customer communication, human decision, refund, credit, debit or chargeback operation is executed

### Requirement: Workflow interrupts
FRD reference: FR-EVD-004, FR-POL-006, FR-CLS-002, FR-WFL-004, FR-ARC-006

The platform SHALL interrupt workflow progression when mandatory evidence is missing, classification is unsupported or below threshold, policy context requires review, or a required downstream capability is unavailable.

#### Scenario: Missing evidence interrupts
- **GIVEN** mandatory evidence is missing for the active workflow
- **WHEN** the evidence gate executes
- **THEN** the workflow is checkpointed with status `WAITING_EVIDENCE`
- **AND** the response identifies the missing-evidence interrupt reason and resume requirements

#### Scenario: Policy review interrupts
- **GIVEN** policy retrieval abstains or requires policy review
- **WHEN** policy-context resolution completes
- **THEN** the workflow is checkpointed with status `WAITING_POLICY_REVIEW`
- **AND** later workflow stages cannot treat missing policy context as approved policy authority

### Requirement: Workflow resume contract
FRD reference: FR-WFL-005, FR-HITL-006, FR-ARC-012

The platform SHALL resume an interrupted workflow only from the latest durable checkpoint using optimistic state-version validation and idempotency controls.

#### Scenario: Workflow resumes from latest checkpoint
- **GIVEN** an interrupted workflow has a durable checkpoint and a valid resume command
- **WHEN** the caller supplies the current workflow state version and idempotency key
- **THEN** the workflow resumes from the checkpoint
- **AND** case ID, workflow ID and correlation ID continue through subsequent state, audit and telemetry records

#### Scenario: Stale resume is rejected
- **GIVEN** a resume command uses a stale workflow state version
- **WHEN** the command is submitted
- **THEN** the command is rejected with HTTP 409 or equivalent structured conflict
- **AND** the existing workflow state remains unchanged
