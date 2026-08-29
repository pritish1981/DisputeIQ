## MODIFIED Requirements

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
