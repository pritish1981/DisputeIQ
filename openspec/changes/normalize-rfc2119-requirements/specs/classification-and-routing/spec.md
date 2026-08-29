## MODIFIED Requirements

### Requirement: Supported dispute classification
FRD reference: FR-CLS-001

The platform SHALL classify valid submitted disputes into supported categories using a versioned structured output containing category and confidence.

#### Scenario: Supported category classified
- GIVEN a valid submitted dispute
- WHEN classification executes
- THEN output conforms to the versioned structured schema
- AND category and confidence are returned

### Requirement: Low-confidence classification gate
FRD reference: FR-CLS-002

The platform SHALL pause automated progression and create a manual-classification HITL task when classification confidence is below the configured threshold.

#### Scenario: Classification confidence below threshold
- GIVEN classification confidence is below configured threshold
- WHEN routing evaluates the result
- THEN automated progression pauses
- AND a manual-classification HITL task is created
