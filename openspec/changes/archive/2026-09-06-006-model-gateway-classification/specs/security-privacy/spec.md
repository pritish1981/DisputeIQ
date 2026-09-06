## ADDED Requirements

### Requirement: Model input data and prompt-injection boundary
FRD reference: FR-SEC-006, FR-AIP-001, FR-AIP-005

The Model Gateway SHALL treat case descriptions, evidence excerpts, provider facts and policy text as untrusted data, enforce configured data policy before provider execution, and prevent untrusted content from changing system prompts, tool permissions, routing policy or financial authority boundaries.

#### Scenario: Prompt-like case content is classified as data
- **GIVEN** a case description or evidence excerpt contains instructions attempting to change system behavior, tool permissions or financial authority
- **WHEN** classification prepares model input
- **THEN** the content is passed only as untrusted data within the approved prompt template
- **AND** system instructions, tool permissions, routing policy and financial authority boundaries are not changed

#### Scenario: Data policy blocks disallowed model input
- **GIVEN** classification input violates configured data policy for the selected model route
- **WHEN** the Model Gateway evaluates the request
- **THEN** model execution is blocked or safely reduced through approved policy
- **AND** automated progression pauses when compliant input cannot be produced
- **AND** the data-policy outcome is observable with correlation ID
