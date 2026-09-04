## Context

See `proposal.md` for motivation. FRD v3.1 defines Phase 004 as `004-hybrid-policy-retrieval`: deterministic policy applicability filters, metadata filtering, lexical plus vector retrieval, fusion/reranking, confidence, citations and RAG regression evaluation. Phase 003 already created controlled policy ingestion, deterministic chunk lineage, pgvector-compatible embedding columns, PostgreSQL lexical-search readiness, promotion gates and policy audit records.

Current code must be reviewed before implementation because earlier memory recorded a policy retrieval conformance gap: application-side token overlap/cosine scoring must not be mistaken for the production pgvector/PostgreSQL retrieval path. This phase should close the runtime retrieval gap over the Phase 003 promoted corpus without introducing LangGraph workflow execution, Model Gateway inference, recommendation generation, HITL task persistence or financial posting.

## Goals / Non-Goals

**Goals:**

- Implement a deterministic Policy Eligibility component for status, effective date, product, channel, jurisdiction and configured applicability metadata.
- Implement a read-only Policy Retrieval service over the active promoted corpus using PostgreSQL lexical search and pgvector vector similarity with deterministic score fusion.
- Preserve complete citation lineage in retrieval outputs: document ID, version, section, chunk ID, chunk hash, effective date range, ingestion run ID, corpus version and index version.
- Implement a confidence/ambiguity gate that returns an abstention plus policy-review HITL signal when retrieval is missing, low-confidence, ambiguous or uncited.
- Record retrieval audit and telemetry/evaluation records with correlation IDs and retrieval configuration versions.
- Prove duplicate-card retrieval quality, citation correctness, metadata filtering and stale/superseded exclusion through regression fixtures and smoke checks.

**Non-Goals:**

- No LangGraph node implementation, workflow checkpointing, interrupt persistence or resume behavior; later workflow phases will consume this service.
- No AI answer generation, recommendation drafting, customer communication or material case decisioning.
- No direct model-provider SDK integration; query embeddings use the existing narrow embedding adapter/test embedding boundary until the Model Gateway phase owns provider-neutral inference.
- No production bank policy connector or real customer data.
- No autonomous refund, credit, debit, chargeback, settlement or posting surface.

## Decisions

### Deterministic eligibility is a separate pre-retrieval boundary

Classify the eligibility filter as deterministic. It accepts request metadata and returns eligible active promoted chunks or an abstention reason before retrieval scoring starts.

Rationale: FR-POL-003 and FR-ARC-004 require eligibility before semantic retrieval, and tests must be able to prove excluded chunks were never ranked.

Alternative considered: apply metadata filters after hybrid scoring. Rejected because an inapplicable chunk could influence rankings or confidence before being removed.

### PostgreSQL executes the production retrieval query

Use database-backed retrieval for the production path: PostgreSQL full-text search for lexical score and pgvector distance/similarity for vector score, restricted to active promoted corpus/index membership.

Rationale: pgvector and PostgreSQL are the authoritative retrieval substrate in the tech stack and Phase 003 prepared those indexes. This directly addresses the known JSON/application-side scoring gap.

Alternative considered: fetch chunks into Python and compute lexical/vector scores in memory. Rejected because it does not prove the required runtime architecture.

### Fusion is deterministic and versioned

Calculate a fused rank from lexical and vector signals with a versioned retrieval configuration that records weights, top-k, minimum confidence threshold, ambiguity threshold and reranker mode. Optional reranking is represented as deterministic metadata unless a later approved phase introduces model-based reranking through the Model Gateway.

Rationale: retrieval behavior must be auditable and reproducible, and FR-POL-008 treats retrieval-index/configuration changes as governed.

Alternative considered: hide weights in code constants. Rejected because evaluation and audit need configuration lineage.

### Confidence gate owns abstention, not human task persistence

The retrieval service returns a structured policy-review HITL signal for missing corpus, no candidates, low fused confidence, ambiguous near-ties or missing citations. It does not create durable HITL tasks until the HITL/workflow phase is active.

Rationale: FR-POL-006 requires abstention and policy-review routing, while later phases own task lifecycle, checkpoint resume and reviewer UI.

Alternative considered: create human-review tasks directly from retrieval APIs. Rejected because it would pull Phase 008 workflow scope into Phase 004.

### Retrieval audit is append-only and blocks accepted success

Successful retrieval and abstention decisions write append-only audit events with corpus/index/config/citation lineage. If audit persistence fails, the retrieval decision is not reported as an accepted success.

Rationale: policy context can affect later recommendations and decisions, so retrieval lineage must be reconstructable under FR-AUD-003/004.

Alternative considered: rely on telemetry only. Rejected because observability logs are not the business audit record.

### Evaluation fixtures are small but adversarial

Create deterministic duplicate-card retrieval fixtures that include eligible policy text, similar stale/superseded text, wrong product/channel/jurisdiction variants, low-confidence queries and citation-lineage checks.

Rationale: the exit gate requires correct citations and retrieval thresholds, not just a happy path.

Alternative considered: reuse Phase 003 promotion metrics only. Rejected because those metrics prove index readiness, not runtime query behavior.

## Risks / Trade-offs

- Existing SQLite-based tests may not support pgvector or PostgreSQL FTS behavior -> Use unit tests for contracts and require PostgreSQL-backed integration/smoke checks for live retrieval proof.
- Local pgvector availability can make developer setup brittle -> Keep deterministic query embedding fixtures and document exact Docker/PostgreSQL readiness checks.
- Score fusion thresholds may need tuning as policies expand -> Version retrieval configuration and treat threshold changes as evaluation-governed.
- The HITL signal is not yet a durable task -> Name it explicitly as a routing contract for later workflow phases and do not imply reviewer task persistence in Phase 004.
- Optional reranking could imply model calls -> Keep Phase 004 reranking deterministic unless a separately approved Model Gateway/reranker dependency is added.

## Migration Plan

1. Review Phase 003 policy tables, indexes, services, schemas, tests and smoke outputs against Phase 004 retrieval specs.
2. Add retrieval request/response schemas, deterministic eligibility and retrieval configuration contracts.
3. Add repository SQL for active promoted corpus lookup, metadata eligibility filtering, PostgreSQL lexical search and pgvector similarity.
4. Add retrieval service ranking, fusion, citation validation, confidence/ambiguity abstention, audit and telemetry/evaluation records.
5. Add protected read-only API or smoke command for duplicate-card retrieval validation.
6. Add regression fixtures/tests for effective-date/product/channel/jurisdiction filtering, stale/superseded exclusion, citation lineage, low confidence, ambiguous results, missing corpus and audit failure.
7. Update runbooks with policy fixture load/promote, retrieval smoke, database proof queries, evaluation thresholds and manual validation.

Rollback strategy: retrieval changes are additive and read-only over the promoted corpus. If validation fails, keep existing ingestion/promotion behavior, disable the retrieval API/smoke path, and do not accept the retrieval configuration for production use.
