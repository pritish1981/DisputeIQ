## MODIFIED Requirements

### Requirement: Grounded recommendation
FRD reference: FR-REC-001, FR-REC-002

The platform SHALL produce structured recommendations grounded in authoritative facts, evidence assessment, policy citations and deterministic rule results, including rationale, references and limitations.

#### Scenario: Recommendation produced
- GIVEN authoritative facts, evidence assessment, policy citations and deterministic rule results are available
- WHEN recommendation generation executes
- THEN a structured recommendation is returned
- AND the output contains rationale, evidence references, policy citations, rule references and limitations

### Requirement: No autonomous execution
FRD reference: FR-REC-003

The recommendation capability SHALL NOT have access to refund, credit, chargeback or other material financial posting tools.

#### Scenario: Recommendation capability tool set evaluated
- GIVEN recommendation generation is running
- WHEN available tools are inspected
- THEN no refund, credit, chargeback or material financial posting tool is available
