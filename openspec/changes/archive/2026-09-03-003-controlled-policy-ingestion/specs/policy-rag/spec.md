## ADDED Requirements

### Requirement: Approved policy corpus ingestion
FRD reference: FR-POL-001

The platform SHALL ingest into the production policy corpus only approved, versioned, active policy documents with valid source identity and integrity metadata.

#### Scenario: Approved active policy is accepted
- **GIVEN** an approved, active, versioned policy document includes source identity, checksum, status, effective dates, product, channel, jurisdiction and section metadata
- **WHEN** controlled policy ingestion is requested
- **THEN** the document is accepted into a non-promoted ingestion run
- **AND** the ingestion result includes document ID, version, checksum, run ID, status and correlation ID

#### Scenario: Unapproved or inactive policy is rejected
- **GIVEN** a policy document is draft, inactive, superseded, missing approval evidence or missing required integrity metadata
- **WHEN** controlled policy ingestion is requested
- **THEN** the document is rejected with a structured validation error
- **AND** the document is not eligible for production retrieval

#### Scenario: Duplicate document version is rejected
- **GIVEN** an active policy document version has already been accepted for the same document ID and version
- **WHEN** another ingestion request uses the same document ID and version with different content or checksum
- **THEN** the request is rejected as a version conflict
- **AND** no existing corpus record is overwritten

### Requirement: Policy metadata preservation
FRD reference: FR-POL-002

The platform SHALL preserve policy document and chunk metadata needed for deterministic applicability, citation reconstruction and audit lineage.

#### Scenario: Policy chunk metadata is retained
- **GIVEN** a policy document passes controlled ingestion validation
- **WHEN** deterministic chunking completes
- **THEN** each chunk retains document ID, version, section, status, effective dates, product, channel, jurisdiction, source checksum, chunk hash and ingestion run ID
- **AND** the metadata is available to downstream retrieval without relying on the original uploaded file

#### Scenario: Missing applicability metadata blocks ingestion
- **GIVEN** a policy document lacks effective date, product, channel or jurisdiction metadata required for deterministic applicability
- **WHEN** controlled policy ingestion validation runs
- **THEN** ingestion fails with field-level validation details
- **AND** no chunks or embeddings from that document are promoted

### Requirement: Deterministic policy chunking lineage
FRD reference: FR-POL-002, FR-POL-005

The platform SHALL split accepted policy documents into deterministic chunks with stable section references and content hashes that support later citation reconstruction.

#### Scenario: Same source yields same chunks
- **GIVEN** the same approved policy document, parser version and chunking configuration are ingested twice in an isolated validation run
- **WHEN** chunking completes
- **THEN** the generated chunk identifiers, section references and chunk hashes are identical

#### Scenario: Chunk citation source can be reconstructed
- **GIVEN** a stored policy chunk is selected for retrieval or evaluation
- **WHEN** its citation lineage is requested
- **THEN** the platform returns the source document ID, version, section, effective date range and ingestion run that produced the chunk

### Requirement: Policy embedding and index promotion
FRD reference: FR-POL-004, FR-POL-008

The platform SHALL generate embeddings and lexical/vector indexes only for validated chunks and SHALL promote a corpus version only after all required ingestion steps and promotion gates succeed.

#### Scenario: Validated chunks are indexed
- **GIVEN** policy chunks have passed validation and deterministic chunking
- **WHEN** embedding generation and indexing complete successfully
- **THEN** the chunks are stored with vector-search and lexical-search index readiness metadata
- **AND** the ingestion run can be promoted as a complete candidate corpus version

#### Scenario: Partial indexing failure blocks promotion
- **GIVEN** parsing, chunking, embedding generation or indexing fails for any required policy document in an ingestion run
- **WHEN** corpus promotion is requested
- **THEN** promotion is blocked
- **AND** the previously promoted corpus remains the production retrieval source

### Requirement: Historical policy isolation
FRD reference: FR-POL-007

The platform SHALL prevent historical case material and non-policy examples from entering the approved production policy corpus unless explicitly marked as evaluation-only data.

#### Scenario: Historical case submitted to policy corpus
- **GIVEN** an ingestion input is historical case content, customer evidence, analyst notes or non-policy example material
- **WHEN** controlled policy ingestion validation runs
- **THEN** the input is rejected for production corpus ingestion
- **AND** it may be stored only as evaluation-only material when explicitly permitted

### Requirement: Reindex governance
FRD reference: FR-POL-008

The platform SHALL treat embedding-model, chunking, parser or retrieval-index configuration changes as versioned reindex events that require regression evaluation before promotion.

#### Scenario: Reindex requires evaluation before promotion
- **GIVEN** an embedding model, parser version, chunking configuration or retrieval-index configuration changes
- **WHEN** a new corpus or index version is built
- **THEN** the platform records a versioned reindex run
- **AND** promotion is blocked until mandatory retrieval and citation regression evaluations pass

#### Scenario: Failed reindex evaluation preserves current corpus
- **GIVEN** a reindex run fails mandatory retrieval or citation regression thresholds
- **WHEN** promotion is requested
- **THEN** the new corpus or index version is not promoted
- **AND** production retrieval continues to use the last promoted corpus version
