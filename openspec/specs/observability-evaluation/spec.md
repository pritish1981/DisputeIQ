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
