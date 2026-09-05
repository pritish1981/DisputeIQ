## ADDED Requirements

### Requirement: Workflow audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-WFL-001, FR-ARC-012

The platform SHALL record workflow starts, node completions, checkpoints, interrupts, resumes and failures as append-only audit-visible events with enough lineage to reconstruct workflow progression.

#### Scenario: Workflow start is audited
- **GIVEN** a workflow start command is accepted
- **WHEN** the workflow run is created
- **THEN** an append-only audit-visible event records case ID, workflow ID, actor, event type, source, graph version, state version, correlation ID and timestamp

#### Scenario: Workflow interrupt is audited
- **GIVEN** workflow execution pauses for missing evidence, policy review, manual classification or manual degradation
- **WHEN** the interrupt checkpoint is persisted
- **THEN** an audit-visible event records workflow ID, node name, interrupt reason, checkpoint sequence, state version and correlation ID

#### Scenario: Workflow audit failure blocks accepted transition
- **GIVEN** a material workflow transition requires audit-visible lineage
- **WHEN** the lineage event cannot be persisted in the accepted operation boundary
- **THEN** the workflow transition is not reported as successful
- **AND** no automated continuation signal is emitted without required lineage
