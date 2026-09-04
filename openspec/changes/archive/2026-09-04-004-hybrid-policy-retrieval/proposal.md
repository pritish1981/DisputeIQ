## Why

Phase 003 established controlled policy ingestion, pgvector-ready chunk storage, lexical index readiness and promotion governance, but production policy resolution still lacks the runtime retrieval contract required by FRD v3.1 Phase 004. This change implements the controlled retrieval layer so duplicate-card investigations can resolve only applicable approved policy context with citations, confidence, abstention and regression evidence before later LangGraph and recommendation phases consume it.

## What Changes

- Add a deterministic policy eligibility/retrieval service that filters active promoted corpus chunks by effective date, status, product, channel, jurisdiction and dispute metadata before semantic retrieval.
- Add hybrid retrieval over the promoted corpus using PostgreSQL lexical search and pgvector vector similarity, with deterministic fusion and optional reranking metadata.
- Return ranked policy context with document ID, version, section, chunk ID, corpus/index versions, scores, configuration version and correlation ID.
- Add a policy confidence gate that abstains on low confidence, ambiguity, missing active corpus or insufficient citations, and returns a policy-review HITL signal without advancing automation.
- Add retrieval/citation regression evaluation fixtures for duplicate-card policy questions, stale/superseded exclusion, metadata filtering and threshold failures.
- Add read-only API/smoke surfaces for retrieval validation without introducing recommendation generation, LangGraph workflow execution or financial posting behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `policy-rag`: Add runtime hybrid retrieval, deterministic applicability filtering, citations, score/confidence contract and abstention behavior for the promoted policy corpus.
- `observability-evaluation`: Add retrieval/citation regression execution and recorded threshold outcomes for retrieval configuration changes.
- `audit-governance`: Add policy retrieval and abstention audit lineage needed to reconstruct which policy corpus, index, chunks and citations were used.
- `architecture-flow-controls`: Preserve the Step 5 boundary that deterministic policy eligibility executes before retrieval and low-confidence policy resolution routes to policy review instead of autonomous continuation.

## Impact

- Backend services/repositories/schemas for policy eligibility, retrieval ranking, confidence gating, retrieval evaluation and retrieval audit events.
- PostgreSQL query paths over Phase 003 policy tables and indexes, including FTS and pgvector-backed SQL rather than JSON/application-only scoring for the production retrieval path.
- Protected read-only API endpoint(s) or smoke command(s) for synthetic duplicate-card retrieval validation.
- Backend unit/integration/evaluation tests, migration/readiness checks, architecture-boundary tests and README/runbook updates.
- No frontend workflow requirement in this phase unless an existing admin/read-only validation panel can be extended without pulling in later HITL or recommendation scope.
