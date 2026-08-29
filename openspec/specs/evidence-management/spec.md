# Evidence Management

## Purpose
Define evidence upload, analysis, deterministic completeness and interrupt/resume.

## Requirements

### Requirement: Deterministic evidence completeness
FRD reference: FR-EVD-003, FR-ARC-003

The platform SHALL determine required, available, missing, stale and conflicting evidence through controlled deterministic logic.

#### Scenario: Evidence checklist evaluated
- GIVEN uploaded evidence and authoritative context exist
- WHEN completeness is evaluated
- THEN required, available, missing, stale and conflicting evidence are identified
- AND mandatory completeness status is produced by controlled deterministic logic

### Requirement: Missing evidence interrupt
FRD reference: FR-EVD-004

The platform SHALL durably checkpoint and interrupt the workflow when mandatory evidence is missing and SHALL resume only after evidence or authorized human disposition.

#### Scenario: Mandatory evidence missing
- GIVEN mandatory evidence is missing
- WHEN the evidence gate executes
- THEN the workflow is durably checkpointed
- AND an evidence request is created
- AND processing resumes only after evidence or authorized human disposition
