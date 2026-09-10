## ADDED Requirements

### Requirement: Versioned applicability decision record
FRD reference: FR-POL-003, FR-POL-005, FR-ARC-004

The platform SHALL apply versioned deterministic eligibility predicates before lexical or vector retrieval and retain the input context, eligible/excluded policy references, reason codes and eligibility configuration version.

#### Scenario: Both search branches use the eligible set
- **GIVEN** approved and inapplicable policy candidates exist for recorded product, channel, jurisdiction, dispute type and transaction effective-as-of date
- **WHEN** policy context is resolved
- **THEN** both lexical and vector retrieval are restricted to the same deterministically eligible corpus members
- **AND** eligibility outcomes and predicate reasons can be reconstructed independently of retrieval scores

#### Scenario: Missing applicability facts abstain
- **GIVEN** a required applicability fact or approved mapping is missing or ambiguous
- **WHEN** policy resolution is requested
- **THEN** retrieval abstains with an explicit policy-review reason
- **AND** customer prose and LLM output cannot supply authoritative applicability defaults

#### Scenario: Policy context mismatches the control profile
- **GIVEN** selected policy versions do not match the pinned evidence/rule profile's approved compatibility references
- **WHEN** the selected policy is admitted to deterministic execution
- **THEN** admission is blocked for policy review
- **AND** the platform cannot infer replacement evidence requirements or rules from retrieved text

### Requirement: Pinned admitted policy context
FRD reference: FR-POL-005, FR-POL-008, FR-AUD-003, FR-AUD-004

The platform SHALL retain exact admitted policy document/version/section/chunk/hash references and corpus/index/retrieval versions for every control evaluation, preserving historical results without replacing them with newly promoted policy.

#### Scenario: Historical replay after corpus promotion
- **GIVEN** an evaluation has admitted policy citations and a newer corpus is promoted
- **WHEN** the historical evaluation is replayed
- **THEN** the recorded policy lineage and deterministic result remain unchanged
- **AND** historical replay does not rerank against the new corpus

#### Scenario: Pinned policy cannot authorize new progression
- **GIVEN** a pinned policy is revoked, unavailable or has an integrity mismatch
- **WHEN** new progression or re-evaluation requires its authority
- **THEN** the workflow pauses for policy review with that reason
- **AND** it does not silently substitute another policy or erase historical lineage
