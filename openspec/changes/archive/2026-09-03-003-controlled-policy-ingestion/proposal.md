## Why

FRD v3.1 defines Phase 003 as Controlled Policy Ingestion so only approved, versioned, active policy material can enter the production retrieval corpus before later hybrid retrieval and workflow orchestration phases consume it. The current OpenSpec policy contract covers deterministic applicability and cited retrieval, but it does not yet define the observable ingestion controls required by `FR-POL-001`, `FR-POL-002`, and `FR-POL-008`.

## What Changes

- Add controlled policy ingestion behavior for approved corpus intake, source validation, status/effective-date checks, and rejection of drafts, inactive policies, malformed metadata, duplicate document versions, or checksum mismatches.
- Persist versioned policy document records, deterministic policy chunks, metadata required by the FRD, embedding/index lineage, source checksums, ingestion run state, and promotion history.
- Generate deterministic chunks with stable section references and chunk hashes so document/version/section citations can be reconstructed by later retrieval and recommendation capabilities.
- Generate embeddings only after deterministic validation passes, store vectors in PostgreSQL/pgvector with lexical-search support, and treat partial parse/chunk/embed/index failures as failed ingestion runs that do not promote an incomplete corpus.
- Add reindex governance for embedding-model, chunking, or retrieval-index changes, including versioned reindex runs, regression evaluation before promotion, and rollback to the last promoted corpus.
- Expose a controlled ingestion API/CLI/admin service surface for synthetic pilot policy fixtures with correlation IDs, structured errors, audit/lineage visibility, and no autonomous financial execution.
- Keep hybrid retrieval ranking, LangGraph policy-resolution nodes, Model Gateway provider routing, recommendation generation, HITL review workflows, communications, and financial posting out of scope.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `policy-rag`: Add controlled policy ingestion, source validation, metadata preservation, deterministic chunking, embedding/index lineage, reindex governance, and corpus promotion behavior for `FR-POL-001`, `FR-POL-002`, `FR-POL-007`, and `FR-POL-008`, while preserving existing applicability, retrieval, citation, and confidence contracts.
- `audit-governance`: Add policy-ingestion and corpus-promotion audit event expectations needed to reconstruct who/what introduced approved policy material into the retrieval corpus.
- `observability-evaluation`: Add ingestion/reindex regression evaluation gates and metrics required before promoting a new policy corpus or index version.
- `security-privacy`: Add untrusted policy source handling so uploaded or imported policy text cannot alter system instructions, tool permissions, or financial authority boundaries.

## Impact

- Backend policy ingestion services, policy repositories, SQLAlchemy models, Alembic migrations, pgvector/FTS schema, embedding adapter boundaries, admin/API or CLI entry points, audit event emission, structured errors, and synthetic policy fixtures.
- Backend unit, integration, migration, policy-ingestion, pgvector/FTS, rollback, idempotency, lineage, audit, evaluation-gate, and architecture-boundary tests.
- RAG evaluation fixtures and scripts proving promoted corpus quality, citation reconstructability, stale/superseded-policy exclusion readiness, and failing-threshold behavior before promotion.
- README/runbook updates for loading synthetic policy fixtures, validating ingestion, inspecting lineage, running reindex evaluation, and verifying no incomplete or unapproved corpus is promoted.
- No customer-facing recommendation, case workflow, LangGraph runtime, HITL task creation, communication generation, or financial posting behavior is introduced by this change.
