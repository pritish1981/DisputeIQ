## MODIFIED Requirements

### Requirement: Governed confidence
FRD reference: FR-CNF-001, FR-CNF-002, FR-ARC-006

The platform SHALL derive case confidence from configured measurable signals and SHALL NOT treat an opaque free-form LLM numeric score as authoritative.

#### Scenario: Case confidence calculated
- GIVEN classification, retrieval, evidence, rule and tool signals are available
- WHEN confidence is calculated
- THEN the result is derived from configured measurable signals
- AND an opaque free-form LLM numeric score is not authoritative

### Requirement: Low-confidence escalation
FRD reference: FR-CNF-003

The platform SHALL pause automated progression and create supervisor or manual review when governed confidence is below the configured threshold.

#### Scenario: Confidence below threshold
- GIVEN governed confidence is below configured threshold
- WHEN the confidence gate executes
- THEN automated progression pauses
- AND supervisor/manual review is created
