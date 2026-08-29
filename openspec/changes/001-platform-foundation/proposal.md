## Why

DisputeIQ needs a deterministic, auditable platform foundation before adding LangGraph orchestration, policy RAG, Model Gateway, HITL decisioning, or AI-assisted capabilities. This change establishes the minimum case, API, persistence, idempotency, synthetic-provider, audit, and UI scaffolding needed to prove a synthetic dispute can be created, replayed, retrieved, and traced safely.

## What Changes

- Add a FastAPI/Pydantic backend foundation for creating and retrieving synthetic dispute cases.
- Add PostgreSQL business-state persistence with Alembic migrations for cases, timeline entries, evidence metadata references, synthetic provider context references, idempotency records, and initial business audit events.
- Add deterministic mandatory intake validation before any workflow execution.
- Add idempotent mutating API behavior using an idempotency key and request fingerprint.
- Add correlation ID handling for accepted API requests and persisted audit/timeline records.
- Add read-only synthetic provider fixtures/interfaces sufficient to attach mock customer/account/transaction context to a created case.
- Add a minimal React/TypeScript UI for case creation, case detail/status display, timeline, evidence metadata, provider context, and audit visibility.
- Add local and GitHub Actions validation for backend lint/tests, frontend lint/tests/build, OpenSpec validation, and baseline dependency/security checks.
- Preserve the explicit architecture boundary that this foundation does not introduce LangGraph runtime execution, LLM calls, policy RAG, Model Gateway, HITL decision workflow, customer communication, or financial posting.

## Capabilities

### New Capabilities

- None. The initialized repository already contains the long-lived capability specs needed for this foundation.

### Modified Capabilities

- `case-intake-and-management`: Implement the first case intake, validation, lifecycle, idempotency, and timeline requirements for synthetic disputes.
- `api-integrations`: Add the initial versioned REST API and correlation ID behavior for case creation and retrieval.
- `audit-governance`: Add the initial immutable business audit event contract and CASE_CREATED audit behavior.
- `authoritative-context`: Add read-only synthetic provider context capture with source lineage for mock banking facts.
- `architecture-flow-controls`: Preserve state-authority separation, deterministic pre-AI intake validation, correlation propagation, and explicit exclusion of autonomous financial execution.

## Impact

- Backend: `backend/app/api`, `backend/app/domain`, `backend/app/services`, `backend/app/adapters`, `backend/app/core`, `backend/tests`.
- Frontend: `frontend/src`, package/test/build configuration.
- Database: PostgreSQL business schema and Alembic migration for foundation entities.
- Mock banking: synthetic fixture/provider contracts under `mock-banking` or backend adapters.
- CI/CD: backend, frontend, OpenSpec, and security baseline GitHub Actions.
- Documentation: README/runbook updates describing startup, validation, API smoke checks, and manual UI verification.
