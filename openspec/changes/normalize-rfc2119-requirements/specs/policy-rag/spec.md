## MODIFIED Requirements

### Requirement: Deterministic policy applicability
FRD reference: FR-POL-003, FR-ARC-004

The platform SHALL deterministically exclude inactive or inapplicable policies before semantic retrieval.

#### Scenario: Policy candidates filtered before semantic search
- GIVEN effective date, product, channel, jurisdiction and dispute context are available
- WHEN policy resolution begins
- THEN inactive or inapplicable policies are excluded deterministically
- AND only eligible candidates proceed to semantic retrieval

### Requirement: Cited controlled retrieval
FRD reference: FR-POL-004, FR-POL-005

The platform SHALL return ranked approved policy context with every material policy claim traceable to its document, version and section.

#### Scenario: Policy context retrieved
- GIVEN eligible policy candidates exist
- WHEN hybrid/vector retrieval and reranking run
- THEN ranked approved context is returned
- AND each material policy claim is traceable to document, version and section

### Requirement: Low policy confidence
FRD reference: FR-POL-006

The platform SHALL stop automated continuation and create policy-review HITL when retrieved policy context is ambiguous or below the configured threshold.

#### Scenario: Retrieval confidence is insufficient
- GIVEN retrieved policy context is ambiguous or below threshold
- WHEN the policy confidence gate executes
- THEN automated continuation is stopped
- AND policy-review HITL is created
