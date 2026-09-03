## ADDED Requirements

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
