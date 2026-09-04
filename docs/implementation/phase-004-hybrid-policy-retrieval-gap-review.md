# Phase 004 Hybrid Policy Retrieval Gap Review

## Source Alignment

Phase 004 follows FRD v3.1 `FR-POL-003`, `FR-POL-004`, `FR-POL-005`, `FR-POL-006`, `FR-AUD-001`, `FR-AUD-002`, `FR-AUD-003`, `FR-AUD-004`, `FR-OBS-001`, `FR-OBS-002`, `FR-OBS-005`, `FR-OBS-006` and `FR-ARC-004`.

The implemented scope is controlled hybrid policy retrieval over the promoted policy corpus only. LangGraph node wiring, Model Gateway LLM calls, recommendation generation, durable HITL task lifecycle, communication and financial posting remain out of scope.

## Existing State Reviewed

- Phase 003 policy tables already persisted policy documents, chunks, ingestion runs, corpus versions, evaluation results and policy audit events.
- Phase 003 migration created pgvector readiness with `vector(8)` embeddings and PostgreSQL lexical readiness with generated `search_tsvector` plus GIN/vector indexes.
- Existing policy APIs covered ingestion, run inspection, promotion and chunk lineage but had no runtime retrieval endpoint.
- Existing evaluation proved corpus promotion readiness but did not prove runtime query behavior, confidence/abstention, retrieval audit lineage or retrieval configuration acceptance.
- SQLAlchemy mapped `embedding_vector` as text for SQLite compatibility while PostgreSQL stores it as pgvector.

## Gaps Closed

- Added retrieval request/response contracts with effective date, product, channel, jurisdiction, actor/service reference, optional case/workflow identifiers, retrieval configuration and correlation ID.
- Added deterministic eligibility filtering against the active promoted corpus before lexical/vector scoring.
- Added PostgreSQL-backed hybrid retrieval using `search_tsvector`, `websearch_to_tsquery`, `ts_rank_cd` and pgvector cosine distance with deterministic fusion.
- Added pgvector insert casting for live PostgreSQL ingestion so Phase 003 chunks can be used by Phase 004 retrieval.
- Added citation lineage in retrieval output without rereading source files.
- Added confidence, ambiguity, missing-corpus, no-candidate and missing-citation abstention responses with policy-review routing signals.
- Added append-only retrieval audit events and rollback behavior for retrieval audit failures.
- Added retrieval regression evaluation records for quality, citation correctness, metadata filtering and stale-policy exclusion.
- Added a protected read-only retrieval API and Phase 004 smoke command.

## Verification Evidence

- Focused retrieval/API tests passed with `16 passed`.
- Full backend pytest passed with `51 passed`.
- `uv run ruff check .` passed after formatting cleanup.
- `uv run mypy app tests` passed with no issues.
- `uv run alembic -c alembic.ini current` reported PostgreSQL revision `20260903_0003 (head)`.
- `uv run python -m app.policy_retrieval_smoke` proved `promoted corpus -> deterministic eligibility -> PostgreSQL lexical search -> pgvector similarity -> fusion/rerank -> cited context -> confidence/audit/evaluation` and returned selected citations, confidence `0.541734`, retrieval status `retrieved`, and passing evaluation metrics.

## Remaining Repository Gate Blocker

- Repository-wide OpenSpec validation may still include historical active change behavior from `normalize-rfc2119-requirements`. Report that separately from the strict target-change validation for `004-hybrid-policy-retrieval`.
