## MODIFIED Requirements

### Requirement: Authoritative banking facts
FRD reference: FR-CTX-001, FR-ARC-002

The platform SHALL obtain banking facts from the designated transaction provider and SHALL NOT replace provider data with LLM-generated facts.

#### Scenario: Transaction context retrieval
- GIVEN a case contains a valid transaction reference
- WHEN the authoritative-context stage executes
- THEN the transaction provider is invoked
- AND provider-returned facts are stored as authoritative context
- AND no LLM-generated fact replaces provider data

### Requirement: Tool authorization
FRD reference: FR-CTX-005

The platform SHALL deny and audit any workflow tool invocation outside the invoking node's allow-list.

#### Scenario: Disallowed tool request
- GIVEN a workflow node attempts to invoke a tool outside its allow-list
- WHEN tool authorization evaluates the call
- THEN the call is denied
- AND the violation is audited
