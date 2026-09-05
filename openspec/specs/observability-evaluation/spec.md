# Observability and AI Evaluation

## Purpose
Define correlated telemetry, AI evaluation, monitoring and release gates.

## Requirements

### Requirement: End-to-end technical correlation
FRD reference: FR-OBS-001, FR-ARC-012

The platform SHALL propagate case ID, workflow ID and correlation ID through API, LangGraph, tool, retrieval and model telemetry.

#### Scenario: Workflow executes
- GIVEN a case and workflow are active
- WHEN API, LangGraph, tool, retrieval and model operations occur
- THEN case ID, workflow ID and correlation ID propagate through telemetry

### Requirement: AI release gates
FRD reference: FR-OBS-005, FR-OBS-006

The platform SHALL run applicable regression, grounding, safety and security evaluations for AI or RAG configuration changes and SHALL block promotion when mandatory thresholds fail.

#### Scenario: AI/RAG configuration changes
- GIVEN model, prompt, embedding, retrieval or rule behavior changes
- WHEN promotion is requested
- THEN applicable regression, grounding, safety and security evaluations run
- AND failed mandatory thresholds block promotion

### Requirement: Policy corpus promotion evaluation
FRD reference: FR-OBS-005, FR-OBS-006, FR-POL-008

The platform SHALL run mandatory retrieval, citation and corpus-integrity regression evaluations before promoting a new policy corpus, embedding index or retrieval-index version.

#### Scenario: Promotion evaluation passes
- **GIVEN** a candidate policy corpus or reindex run has completed ingestion and indexing
- **WHEN** promotion evaluation runs
- **THEN** retrieval quality, citation correctness, metadata integrity and stale-policy exclusion checks are evaluated against configured thresholds
- **AND** passing results are recorded with corpus version, index version and correlation ID

#### Scenario: Promotion evaluation fails
- **GIVEN** a candidate policy corpus or reindex run fails a mandatory threshold
- **WHEN** promotion is requested
- **THEN** promotion is denied with a structured evaluation failure
- **AND** the failure is visible in operational evaluation records

### Requirement: Policy retrieval regression evaluation
FRD reference: FR-OBS-005, FR-OBS-006, FR-POL-004, FR-POL-005, FR-POL-008

The platform SHALL run retrieval and citation regression evaluations for policy retrieval configuration changes and SHALL record threshold outcomes before a retrieval configuration is accepted for production use.

#### Scenario: Retrieval regression passes
- **GIVEN** a promoted policy corpus and candidate retrieval configuration are available
- **WHEN** the retrieval regression suite runs
- **THEN** duplicate-card retrieval quality, citation correctness, metadata filtering and stale-policy exclusion are evaluated against configured thresholds
- **AND** passing results are recorded with corpus version, index version, retrieval configuration version and correlation ID

#### Scenario: Retrieval regression fails
- **GIVEN** a retrieval configuration fails a mandatory retrieval or citation threshold
- **WHEN** acceptance is requested
- **THEN** the retrieval configuration is not accepted for production use
- **AND** the failed metric, expected threshold and correlation ID are visible in evaluation records

### Requirement: Policy retrieval telemetry
FRD reference: FR-OBS-001, FR-OBS-002, FR-ARC-012

The platform SHALL emit correlated retrieval telemetry that can reconstruct policy resolution latency, candidate counts, result counts, confidence and abstention reason.

#### Scenario: Retrieval telemetry is correlated
- **GIVEN** policy retrieval executes for a case or validation request
- **WHEN** telemetry is recorded
- **THEN** the telemetry includes case ID when available, workflow ID when available, correlation ID, corpus version, index version, retrieval configuration version, eligible candidate count, returned result count and confidence outcome

#### Scenario: Abstention telemetry is correlated
- **GIVEN** policy retrieval abstains because of missing corpus, no candidates, ambiguity, low confidence or missing citations
- **WHEN** telemetry is recorded
- **THEN** the abstention reason is correlated with the policy retrieval request and visible for operational diagnostics

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
