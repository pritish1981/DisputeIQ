## MODIFIED Requirements

### Requirement: Deterministic evidence completeness
FRD reference: FR-EVD-003, FR-ARC-003

The platform SHALL determine required, available, missing, stale and conflicting evidence through controlled deterministic logic.

#### Scenario: Evidence checklist evaluated
- GIVEN uploaded evidence and authoritative context exist
- WHEN completeness is evaluated
- THEN required, available, missing, stale and conflicting evidence are identified
- AND mandatory completeness status is produced by controlled deterministic logic

#### Scenario: Phase 002 evidence metadata persists without AI analysis
- **GIVEN** a Phase 002 synthetic duplicate-card case contains evidence metadata
- **WHEN** evidence metadata is registered or returned
- **THEN** the metadata is persisted and retrieved without invoking AI-assisted document analysis
- **AND** any completeness status exposed by Phase 002 is deterministic and marked as preliminary when full workflow evidence gates are not yet enabled

### Requirement: Missing evidence interrupt
FRD reference: FR-EVD-004

The platform SHALL durably checkpoint and interrupt the workflow when mandatory evidence is missing and SHALL resume only after evidence or authorized human disposition.

#### Scenario: Mandatory evidence missing
- GIVEN mandatory evidence is missing
- WHEN the evidence gate executes
- THEN the workflow is durably checkpointed
- AND an evidence request is created
- AND processing resumes only after evidence or authorized human disposition
