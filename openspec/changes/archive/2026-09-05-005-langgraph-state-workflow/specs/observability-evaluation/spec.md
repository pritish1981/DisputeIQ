## ADDED Requirements

### Requirement: Workflow telemetry
FRD reference: FR-OBS-001, FR-OBS-002, FR-ARC-012

The platform SHALL emit correlated workflow telemetry for starts, node execution, checkpoints, interrupts, resumes, retries, latency and terminal or paused outcomes.

#### Scenario: Node telemetry is correlated
- **GIVEN** a workflow node executes
- **WHEN** telemetry is recorded
- **THEN** the telemetry includes case ID, workflow ID, node name, graph version, state version, correlation ID, attempt count, status and latency

#### Scenario: Interrupt telemetry is correlated
- **GIVEN** workflow execution pauses at an interrupt
- **WHEN** telemetry is recorded
- **THEN** the telemetry includes interrupt type, checkpoint sequence, current node, case ID, workflow ID and correlation ID

### Requirement: Workflow validation suite
FRD reference: FR-OBS-005, FR-OBS-006, FR-WFL-005

The platform SHALL include automated validation that proves workflow graph routing, checkpoint persistence, safe resume, interrupt behavior, audit lineage and no-autonomous-financial-execution boundaries before Phase 005 is accepted.

#### Scenario: Phase 005 validation passes
- **GIVEN** Phase 005 implementation is complete
- **WHEN** the validation suite runs
- **THEN** tests prove duplicate-card workflow start, checkpointing, controlled interrupts, resume safety, audit lineage, telemetry correlation and architecture boundaries
- **AND** no model-provider direct call, customer communication or financial posting capability is required for the Phase 005 validation path
