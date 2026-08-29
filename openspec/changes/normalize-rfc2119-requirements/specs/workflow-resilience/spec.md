## MODIFIED Requirements

### Requirement: Durable checkpoint authority
FRD reference: FR-WFL-001, FR-ARC-011

The platform SHALL durably persist checkpoint state at material workflow boundaries and interrupts, and Redis SHALL NOT be the sole durable authority.

#### Scenario: Material workflow boundary reached
- GIVEN LangGraph reaches a material stage boundary or interrupt
- WHEN checkpointing occurs
- THEN checkpoint state is durably persisted
- AND Redis is not the sole durable authority

### Requirement: Safe resume
FRD reference: FR-WFL-005

The platform SHALL resume interrupted workflows without duplicating completed external side effects.

#### Scenario: Workflow restarts after interruption
- GIVEN completed external side effects already exist
- WHEN the workflow resumes from a checkpoint
- THEN completed side effects are not duplicated
