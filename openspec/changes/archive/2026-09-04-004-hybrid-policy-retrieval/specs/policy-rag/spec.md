## MODIFIED Requirements

### Requirement: Deterministic policy applicability
FRD reference: FR-POL-003, FR-ARC-004

The platform SHALL deterministically exclude inactive, unapproved, superseded or inapplicable policies before lexical or semantic retrieval.

#### Scenario: Policy candidates filtered before semantic search
- **GIVEN** effective date, product, channel, jurisdiction and dispute context are available
- **WHEN** policy resolution begins
- **THEN** inactive or inapplicable policies are excluded deterministically
- **AND** only eligible candidates from the active promoted corpus proceed to lexical and vector retrieval

#### Scenario: No applicable policy candidates
- **GIVEN** no active promoted policy chunks match the effective date, product, channel, jurisdiction and dispute context
- **WHEN** policy resolution begins
- **THEN** no lexical or vector retrieval is attempted against inapplicable chunks
- **AND** the policy resolution result abstains with a policy-review HITL signal

### Requirement: Cited controlled retrieval
FRD reference: FR-POL-004, FR-POL-005

The platform SHALL return ranked approved policy context from the active promoted corpus using metadata filtering plus lexical and vector retrieval, with every material policy claim traceable to its document, version and section.

#### Scenario: Policy context retrieved
- **GIVEN** eligible policy candidates exist in the active promoted corpus
- **WHEN** hybrid/vector retrieval and reranking run
- **THEN** ranked approved context is returned
- **AND** each material policy claim is traceable to document, version and section

#### Scenario: Hybrid retrieval uses lexical and vector evidence
- **GIVEN** eligible policy chunks exist for a duplicate-card dispute
- **WHEN** policy retrieval runs
- **THEN** the result includes lexical score, vector score, fused score and rank for each returned chunk
- **AND** the retrieval result identifies the corpus version, index version, retrieval configuration version and correlation ID

#### Scenario: Stale or superseded policy is excluded from results
- **GIVEN** approved active, stale, inactive and superseded policy chunks exist for similar policy text
- **WHEN** retrieval runs for an effective duplicate-card dispute date
- **THEN** returned policy context includes only chunks that are effective and active for that request
- **AND** stale, inactive and superseded chunks are absent from ranked context and citations

#### Scenario: Citation lineage is complete
- **GIVEN** a policy chunk is selected for ranked context
- **WHEN** the retrieval response is produced
- **THEN** the response includes document ID, version, section, chunk ID, chunk hash, effective date range and ingestion run ID
- **AND** downstream recommendation or review stages can cite the policy without reading the original source file

### Requirement: Low policy confidence
FRD reference: FR-POL-006

The platform SHALL stop automated continuation and create a policy-review HITL signal when retrieved policy context is missing, ambiguous, uncited or below the configured threshold.

#### Scenario: Retrieval confidence is insufficient
- **GIVEN** retrieved policy context is ambiguous or below threshold
- **WHEN** the policy confidence gate executes
- **THEN** automated continuation is stopped
- **AND** policy-review HITL is created

#### Scenario: Missing active corpus abstains
- **GIVEN** no promoted production policy corpus is active
- **WHEN** policy resolution is requested
- **THEN** the retrieval result abstains with a structured reason
- **AND** policy-review HITL is created without inventing policy context

#### Scenario: Missing citation blocks continuation
- **GIVEN** retrieval returns text without complete document, version, section and chunk lineage
- **WHEN** the policy confidence gate executes
- **THEN** the result is treated as insufficient policy confidence
- **AND** automated continuation is stopped for policy review
