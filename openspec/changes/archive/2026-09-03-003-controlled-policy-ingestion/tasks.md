## 1. Gap Review and Source Alignment

- [x] 1.1 Review existing policy models, migrations, repositories, services, fixtures, retrieval code, evaluation scripts and README against `FR-POL-001`, `FR-POL-002`, `FR-POL-007`, `FR-POL-008`, `FR-AUD-001`, `FR-AUD-002`, `FR-OBS-005`, `FR-OBS-006` and `FR-SEC-006`; verify the review identifies reusable code, JSON/application-side scoring gaps, missing pgvector/FTS proof, and missing ingestion lineage.
- [x] 1.2 Confirm the Phase 003 scope is ingestion and corpus/index promotion only, with hybrid retrieval ranking, LangGraph orchestration, recommendation, HITL workflow, communication and financial posting out of scope; verify architecture-boundary tests or review notes name the excluded runtime paths.

## 2. Policy Corpus Persistence and Migration

- [x] 2.1 Add or correct PostgreSQL/Alembic schema for policy documents, document versions, policy chunks, ingestion runs, embedding records, lexical/vector index metadata, corpus versions, active promotion pointer, evaluation results and audit links; verify Alembic upgrade succeeds against the local PostgreSQL test database.
- [x] 2.2 Persist required document and chunk metadata for document ID, version, section, status, effective dates, product, channel, jurisdiction, source checksum, chunk hash, parser/chunking configuration, embedding model/configuration, ingestion run ID and correlation ID; verify repository tests create and retrieve all required lineage fields.
- [x] 2.3 Prove pgvector and PostgreSQL lexical-search readiness for validated chunks using database-backed tests or SQL smoke checks; verify tests fail if embeddings are stored only as JSON blobs or lexical scoring runs only in application code.

## 3. Deterministic Validation and Chunking

- [x] 3.1 Implement deterministic ingestion validation for source identity, approval status, active status, document/version uniqueness, checksum, effective dates, product, channel, jurisdiction and section metadata; verify tests accept an approved active policy and reject draft, inactive, superseded, malformed and checksum-mismatched inputs.
- [x] 3.2 Implement duplicate document/version conflict detection that preserves the existing corpus record; verify conflicting content or checksum for the same document ID and version returns a structured conflict with no overwrite.
- [x] 3.3 Implement deterministic parsing and chunking with stable section references, chunk IDs and chunk hashes; verify repeated isolated runs for the same document/parser/chunking configuration produce identical chunks.
- [x] 3.4 Implement historical/non-policy source isolation for case history, customer evidence, analyst notes and non-policy examples; verify production corpus ingestion rejects them and evaluation-only storage is allowed only when explicitly marked.

## 4. Embedding, Indexing and Promotion

- [x] 4.1 Implement the embedding adapter boundary so embeddings run only after validation and chunking succeed, record model/configuration metadata, and expose no case mutation, recommendation, communication or financial posting tools; verify unit and architecture-boundary tests cover the restricted adapter contract.
- [x] 4.2 Implement vector and lexical indexing for validated chunks with run/index readiness state; verify integration tests show a complete candidate run has indexed chunks and failed parse/chunk/embed/index steps leave the run non-promotable.
- [x] 4.3 Implement versioned corpus/index promotion with rollback-safe active pointer semantics; verify promotion succeeds only for complete runs and partial failures preserve the previous promoted corpus.
- [x] 4.4 Implement reindex governance for parser, chunking, embedding-model and retrieval-index configuration changes; verify a changed configuration creates a versioned reindex run and cannot promote until mandatory evaluations pass.

## 5. Admin API, Fixture Loader and Structured Errors

- [x] 5.1 Add protected admin API endpoints for policy ingestion, ingestion-run inspection and corpus/index promotion with Pydantic contracts, correlation propagation and structured errors; verify API tests cover success, validation failure, version conflict, unauthorized caller, not found and failed promotion.
- [x] 5.2 Add a synthetic policy fixture loader or smoke script that exercises the same ingestion service/API path as the admin endpoints; verify it loads approved duplicate-card policy fixtures and stale/superseded negative fixtures with identical audit and lineage behavior.
- [x] 5.3 Expose citation-lineage reconstruction for stored chunks by document ID, version, section, effective date range and ingestion run; verify tests reconstruct lineage without reading the original uploaded/source file.

## 6. Audit, Security and Observability

- [x] 6.1 Emit append-only audit events for accepted ingestion, rejected ingestion, validation failure, reindex creation, promotion success and promotion denial; verify audit tests include actor, timestamp, event type, source, correlation ID, document/version/checksum, run ID, corpus/index version and decision status.
- [x] 6.2 Enforce policy source untrusted-content handling so prompt-like policy text cannot change system instructions, authorization, tool permissions or financial authority boundaries; verify security tests process malicious-looking policy text as data only.
- [x] 6.3 Add telemetry/evaluation records for ingestion run state, validation errors, embedding/index readiness, evaluation results, promotion decisions and correlation IDs; verify observability tests or smoke output expose the required fields.

## 7. Evaluation Gates and Documentation

- [x] 7.1 Add policy corpus promotion evaluations for retrieval quality, citation correctness, metadata integrity and stale/superseded-policy exclusion; verify passing fixtures meet configured thresholds and failing fixtures block promotion with structured results.
- [x] 7.2 Update README/runbook for controlled policy ingestion, synthetic fixture loading, lineage inspection, pgvector/lexical readiness checks, reindex evaluation, promotion, rollback and manual validation; verify commands and expected outputs are documented.
- [x] 7.3 Run backend `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest` from `backend/`; verify all policy ingestion, repository, migration, API, audit, security, evaluation and architecture-boundary tests pass.
- [x] 7.4 Run a synthetic Phase 003 smoke proving `validated -> chunked -> embedded -> indexed -> evaluated -> promoted -> audited` with no LangGraph, recommendation, HITL, communication or financial posting behavior; verify output records corpus version, index version, run ID, correlation ID, lineage and audit events.
- [x] 7.5 Run `npx.cmd -y @fission-ai/openspec@1.10.0 validate --changes "003-controlled-policy-ingestion" --strict` and `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`; verify strict validation passes before requesting implementation review.
