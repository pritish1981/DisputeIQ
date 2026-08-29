# Human in the Loop

## Purpose
Define mandatory human decisioning, review package, actions, rationale and resume.

## Requirements

### Requirement: Mandatory material review
FRD reference: FR-HITL-001, FR-ARC-008

The platform SHALL require authorized human review before recording any final material outcome.

#### Scenario: Recommendation reaches decision stage
- GIVEN a material recommendation is ready
- WHEN the workflow reaches Human Decision
- THEN a human review task is created
- AND final material outcome is not recorded before authorized review

### Requirement: Reviewer actions
FRD reference: FR-HITL-003

The platform SHALL support Approve, Modify, Reject and Request Rework actions and retain required rationale and reviewer identity.

#### Scenario: Reviewer decides case
- GIVEN an authorized reviewer has the decision package
- WHEN the reviewer acts
- THEN Approve, Modify, Reject and Request Rework are supported
- AND required rationale and reviewer identity are retained
