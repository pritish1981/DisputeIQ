# Security and Privacy

## Purpose
Define identity, authorization, encryption, secrets, PII minimization and prompt-injection boundaries.

## Requirements

### Requirement: Protected access
FRD reference: FR-SEC-001, FR-SEC-002

The platform SHALL deny protected operations when the caller lacks the required identity, role or case permission and SHALL make the security event observable.

#### Scenario: Unauthorized access attempt
- GIVEN a caller lacks the required identity or role/case permission
- WHEN a protected operation is requested
- THEN access is denied
- AND the security event is observable

### Requirement: Untrusted-content boundary
FRD reference: FR-SEC-006

The platform SHALL treat uploaded and retrieved content as untrusted data and SHALL NOT allow it to override system instructions or tool permissions.

#### Scenario: Evidence contains prompt-like instructions
- GIVEN uploaded or retrieved content contains instructions attempting to change system behavior
- WHEN the content is processed
- THEN it remains untrusted data
- AND system instructions and tool permissions are not overridden

### Requirement: Policy source content remains untrusted
FRD reference: FR-SEC-006, FR-POL-001

The platform SHALL treat imported policy source text and metadata as untrusted content and SHALL NOT allow policy content to alter system instructions, tool permissions, authorization rules or financial authority boundaries.

#### Scenario: Policy source contains prompt-like instructions
- **GIVEN** imported policy source content includes instructions that attempt to change system behavior, tool permissions, authorization rules or financial authority
- **WHEN** controlled policy ingestion processes the source
- **THEN** the content is stored only as policy data if all validation rules pass
- **AND** system instructions, tool permissions, authorization rules and financial authority boundaries are not changed

#### Scenario: Unauthorized caller requests ingestion
- **GIVEN** a caller lacks the required policy-admin role or permission
- **WHEN** controlled policy ingestion or corpus promotion is requested
- **THEN** access is denied
- **AND** the denial is observable with correlation ID and security event metadata

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
