# Phase 003 Controlled Policy Ingestion Gap Review

## Source Alignment

Phase 003 follows FRD v3.1 `FR-POL-001`, `FR-POL-002`, `FR-POL-007`, `FR-POL-008`, `FR-AUD-001`, `FR-AUD-002`, `FR-OBS-005`, `FR-OBS-006` and `FR-SEC-006`.

The implemented scope is controlled policy ingestion and corpus/index promotion only. LangGraph orchestration, hybrid retrieval answer generation, recommendation, HITL workflow, communication, and financial posting remain out of scope.

## Existing State Reviewed

- `backend/app/adapters/models.py` contained only Phase 002 case, evidence, provider context, idempotency, timeline, and case audit models.
- `backend/app/adapters/repositories.py` contained Phase 002 case/evidence/provider/audit repositories.
- `backend/app/domain/schemas.py` contained case and evidence schemas, but no policy ingestion contracts.
- `backend/app/main.py` routed cases and dispute compatibility routes only.
- `backend/alembic/versions/` contained Phase 001 and Phase 002 migrations only.
- Existing tests covered no-LangGraph/no-LLM Phase 002 boundaries and no policy ingestion surface.
- The repo-level `rag/README.md` reserved controlled policy RAG but did not implement ingestion.

## Gaps Identified

- No durable policy document, chunk, ingestion-run, corpus-version, evaluation-result, or policy-audit tables.
- No source validation for approved/active policy status, approval references, source identity, checksums, effective dates, product, channel, jurisdiction, or source type.
- No deterministic chunk IDs, section lineage, parser/chunking configuration, embedding configuration, or chunk hashes.
- No protected admin ingestion API or run-inspection/promotion/lineage endpoints.
- No pgvector/FTS migration proof for Phase 003 policy chunks.
- No promotion gate preserving the last active corpus when validation, indexing, audit, or evaluation fails.
- No policy ingestion audit events or promotion-denial/promotion-success lineage.
- No untrusted-content test for prompt-like policy source text.

## Reuse Decisions

- Reuse the existing FastAPI/Pydantic/SQLAlchemy/repository/service/test patterns.
- Reuse the existing correlation ID and structured error envelope behavior.
- Keep Phase 002 case APIs deterministic and update architecture tests so they remain protected while allowing the new isolated policy ingestion path.

## Verification Evidence

- `uv run ruff check .` passed.
- `uv run mypy app tests` passed.
- `uv run pytest` passed with `41 passed`.
- `uv run python -m app.policy_ingestion_smoke` proved `validated -> chunked -> embedded -> indexed -> evaluated -> promoted -> audited` and printed run ID, corpus version, index version, correlation ID, chunk lineage, and audit events.
- `uv run alembic -c alembic.ini upgrade head --sql` generated PostgreSQL DDL with `CREATE EXTENSION IF NOT EXISTS vector`, `vector(8)`, `search_tsvector`, GIN, and vector cosine index statements.
- `uv run alembic -c alembic.ini upgrade head` upgraded the local Compose PostgreSQL database from `20260830_0002` to `20260903_0003`.
- PostgreSQL verification returned Phase 003 revision `20260903_0003`, all six policy tables, policy chunk FTS/vector indexes, and the `vector` extension.
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate 003-controlled-policy-ingestion --type change --strict` passed.

## Remaining Repository Gate Blocker

- Repository-wide `openspec validate --all --strict` is still blocked by the pre-existing `normalize-rfc2119-requirements` change, not by `003-controlled-policy-ingestion`.
