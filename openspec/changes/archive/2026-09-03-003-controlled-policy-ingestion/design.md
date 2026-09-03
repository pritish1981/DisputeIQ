## Context

See `proposal.md` for motivation. FRD v3.1 defines Phase 003 as Controlled Policy Ingestion: approved/versioned policy ingestion, source validation, effective-date and applicability metadata, deterministic chunking, embedding generation, pgvector indexing and ingestion lineage. Long-lived `policy-rag` specs already define downstream applicability, retrieval, citations and confidence, but the ingestion side must become explicit before hybrid retrieval and LangGraph policy-resolution stages consume policy context.

The existing repository may contain policy RAG code from earlier work. Implementation must treat the approved OpenSpec and FRD as authoritative, and must close any gap where runtime behavior uses in-memory or JSON-only vector scoring instead of PostgreSQL/pgvector and lexical-search-backed indexing for the production-style pilot.

## Goals / Non-Goals

**Goals:**

- Establish deterministic policy ingestion validation before parsing, chunking, embedding or promotion.
- Persist policy documents, chunks, source checksums, applicability metadata, ingestion runs, embedding/index lineage, evaluation results and promotion history in PostgreSQL-backed stores.
- Build pgvector-backed vector index readiness and PostgreSQL lexical-search readiness as the durable retrieval substrate for later hybrid retrieval.
- Make corpus promotion atomic: either a complete, evaluated corpus/index version is promoted, or production retrieval continues using the previous promoted corpus.
- Emit audit and telemetry for ingestion decisions, validation failures, reindex runs, evaluation gates and promotion decisions.
- Preserve untrusted-content and role/permission boundaries for imported policy source material.

**Non-Goals:**

- No LangGraph policy-resolution node, workflow checkpointing or case workflow integration.
- No recommendation generation, customer communication drafting, HITL review UI, or material financial decisioning.
- No autonomous refund, credit, debit, chargeback or settlement posting surface.
- No live bank policy import connector; this phase uses controlled admin/API or CLI ingestion of synthetic pilot policy fixtures.
- No retrieval answer generation; this phase prepares the corpus and proves indexing, lineage and promotion gates.

## Decisions

### Deterministic Ingestion Service Owns Acceptance

Implement a deterministic ingestion service that validates source identity, approval status, active status, document/version uniqueness, checksum, effective dates, product, channel, jurisdiction and section metadata before any chunk or embedding work begins.

Rationale: `FR-POL-001` and `FR-POL-002` require approved corpus and metadata controls before production retrieval. Validation must not depend on LLM interpretation.

Alternative considered: allow ingestion to parse first and reject later. Rejected because malformed or unapproved policy content could leak into chunk, embedding or evaluation stores and weaken corpus lineage.

### PostgreSQL Owns Policy Corpus State

Represent policy documents, chunks, ingestion runs, embedding records, index versions, evaluation results and promotion state in PostgreSQL. Store vector embeddings using pgvector-compatible columns and maintain lexical-search materialization/indexes for later hybrid retrieval.

Rationale: The tech stack and architecture invariants make PostgreSQL/pgvector the durable RAG store. Redis remains transient only and cannot own corpus membership.

Alternative considered: JSON embedding blobs with application-side cosine scoring. Rejected because it does not prove the required PostgreSQL vector and lexical retrieval architecture.

### Deterministic Chunking Produces Stable Citation Units

Chunking uses parser version, chunking configuration, source checksum and policy section boundaries to produce stable chunk IDs and chunk hashes. Chunk records retain document ID, version, section and applicability metadata even after the source artifact is unavailable.

Rationale: Later retrieval and recommendation claims need document/version/section citations under `FR-POL-005`; citation reconstruction must not depend on re-parsing raw files.

Alternative considered: token-window-only chunks with generated identifiers. Rejected because IDs can drift across parser/configuration changes and break lineage.

### Embedding Adapter Is Isolated From Financial Authority

Embedding generation is an AI-adjacent adapter capability used only after deterministic validation passes. It receives policy text chunks and returns embeddings plus model/configuration metadata. It cannot access case mutation, recommendation, communication or financial posting tools.

Rationale: This keeps AI-assisted indexing separate from authoritative financial facts and material case outcomes.

Alternative considered: reuse a general Model Gateway path immediately. Deferred because Phase 006 owns provider-neutral Model Gateway behavior; this phase needs a narrow embedding boundary and recorded model/configuration metadata.

### Promotion Is Versioned and Gate-Controlled

An ingestion or reindex run creates a candidate corpus/index version. Promotion requires all documents and chunks in the run to finish parsing, chunking, embedding, indexing and evaluation. Promotion writes a single active production corpus pointer and audit event in one accepted operation boundary.

Rationale: Production retrieval should never see partial or failed indexes, and reindex changes under `FR-POL-008` require regression evaluation before promotion.

Alternative considered: immediately make indexed chunks queryable as they arrive. Rejected because partial corpus exposure can produce stale, missing or uncited policy context.

### Evaluation Gates Use Synthetic Policy Fixtures

Add deterministic evaluation fixtures for duplicate-card policy questions, expected sections, excluded stale/superseded policies, and citation correctness. Promotion fails when configured mandatory thresholds fail, and the failure remains inspectable.

Rationale: This proves the corpus can support later retrieval quality without implementing the full workflow or recommendation phases.

Alternative considered: rely only on unit tests. Rejected because ingestion success and retrieval readiness need corpus-level quality and citation checks.

### Policy Source Content Is Untrusted Data

Policy text is data. It may include prompt-like language because policies are natural-language documents, but ingestion must not interpret it as system instructions, authorization changes, tool permissions or financial authority.

Rationale: `FR-SEC-006` applies to uploaded and retrieved content, and policy import is a high-value injection boundary.

Alternative considered: treat approved policy content as trusted instructions. Rejected because approval for policy retrieval does not grant runtime control over system behavior.

### Controlled Surface Is Service-First With Admin API and Fixture Loader

Implement one deterministic ingestion service and expose it through protected admin API endpoints for ingestion, run inspection and promotion. Add a small fixture loader or smoke script only as an operational convenience for synthetic pilot data; it must call the same service or API path and produce the same audit, lineage, validation and promotion behavior.

Rationale: The API gives an observable contract for tests and later admin UI work, while the fixture loader keeps local validation repeatable without inventing a second ingestion path.

Alternative considered: CLI-only ingestion. Rejected because it would under-specify the protected operational contract later workflow and admin surfaces rely on.

## Risks / Trade-offs

- Existing policy implementation may already expose retrieval APIs with JSON/application-side scoring -> Mitigation: add implementation tasks and tests that prove pgvector and lexical-search-backed indexing/readiness before claiming Phase 003 completion.
- Embedding provider availability can make local development brittle -> Mitigation: define deterministic test embedding fixtures and a narrow embedding adapter, while recording real embedding metadata when configured.
- Corpus promotion atomicity can be subtle across tables -> Mitigation: use repository/service tests that force parse, embed, index, evaluation and audit failures and assert the promoted corpus pointer is unchanged.
- Policy ingestion API shape could drift from later admin needs -> Mitigation: keep this phase to minimal protected admin endpoints for ingestion, run inspection and promotion, with fixture loading routed through the same service contract.
- Evaluation thresholds may evolve in Phase 004 retrieval work -> Mitigation: version evaluation configuration and treat threshold changes as reindex/promotion-governed configuration.

## Migration Plan

1. Review existing policy models, migrations, services, fixtures, retrieval code and evaluation scripts against the Phase 003 specs.
2. Add or correct migrations for policy documents, chunks, ingestion runs, embedding/index lineage, corpus versions, promotion pointers, evaluation results and audit links.
3. Implement deterministic validation, parsing/chunking, embedding adapter boundary, pgvector/lexical indexing, promotion and rollback semantics.
4. Load synthetic approved policy fixtures and stale/superseded negative fixtures.
5. Run backend lint/type/unit/integration/migration tests, policy ingestion smoke, pgvector/lexical readiness checks, evaluation gates and OpenSpec strict validation.

Rollback strategy: keep the previous promoted corpus pointer unchanged until a candidate passes all gates. If a deployed migration must be reverted during the synthetic pilot, roll back the new policy-ingestion tables/indexes and restore the previous policy retrieval fixture behavior only after documenting the deviation.
