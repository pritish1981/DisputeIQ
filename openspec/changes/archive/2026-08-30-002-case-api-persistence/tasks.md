## 1. Phase 001 Gap Review and Contract Alignment

- [x] 1.1 Review existing backend models, migrations, schemas, repositories, services, routes, tests, and README against `FR-CAS-001` through `FR-CAS-005`; verify the review identifies reuse versus gaps for case entity, lifecycle status, timestamps, idempotency, timeline, retrieval, and replay.
- [x] 1.2 Review existing evidence metadata, provider context, and audit implementations against `FR-EVD-001` through `FR-EVD-003`, `FR-CTX-001` through `FR-CTX-005`, and `FR-AUD-001` through `FR-AUD-002`; verify the review identifies missing provider breadth, metadata fields, audit fields, and endpoint gaps.
- [x] 1.3 Decide and document the `/api/v1/disputes` transition approach while making `/api/v1/cases` canonical; verify OpenAPI and README/API docs describe the canonical Phase 002 surface.

## 2. Case Domain and Persistence

- [x] 2.1 Extend or confirm the case persistence model for case ID, customer reference, transaction reference, optional account reference, channel, channel metadata, dispute description, lifecycle status, opened/updated/closed timestamps, correlation ID, and monotonic `state_version`; verify repository/model tests cover create and retrieve for all required fields.
- [x] 2.2 Add or confirm migration coverage for Phase 002 case, idempotency, timeline, evidence metadata, provider context, and audit tables/indexes/constraints; verify Alembic upgrade succeeds against the local PostgreSQL test database.
- [x] 2.3 Add case lifecycle status constants and transition validation for the Phase 002 intake/submitted state; verify unit tests cover valid initialization and rejection of unsupported direct transitions.
- [x] 2.4 Add optimistic locking support for material case aggregate mutations using `If-Match` or equivalent expected version; verify stale-version tests return a structured conflict and leave persisted state unchanged.

## 3. Case API Contracts

- [x] 3.1 Implement canonical `POST /api/v1/cases` with Pydantic request/response schemas, mandatory validation, idempotency key requirement, correlation propagation, and duplicate-card-only Phase 002 validation; verify API tests cover success, missing fields, unsupported dispute type, missing idempotency key, and correlation behavior.
- [x] 3.2 Implement safe idempotent create replay using operation, idempotency key, and logical request fingerprint; verify replay returns the original result without creating a second case or second `CASE_CREATED` audit event.
- [x] 3.3 Implement idempotency conflict handling for reused keys with different payloads; verify API/service tests reject the conflict without new case, timeline, provider, or audit side effects.
- [x] 3.4 Implement `GET /api/v1/cases/{case_id}` with case summary, lifecycle status, references, timestamps, channel metadata, state version, evidence metadata summary, provider context lineage, timeline summary, audit visibility, and correlation fields; verify API tests cover found and not-found cases.
- [x] 3.5 Implement MVP case listing/search by supported metadata such as status, customer reference, transaction reference, channel, and opened date range; verify tests cover deterministic ordering, supported filters, unsupported filters, and unauthorized data isolation assumptions.
- [x] 3.6 Preserve `/api/v1/disputes` compatibility only if retained as a thin delegate to the canonical case service; verify compatibility tests prove identical persistence/idempotency behavior or remove/update stale tests and docs.

## 4. Evidence Metadata APIs

- [x] 4.1 Implement evidence metadata registration for existing cases with Pydantic validation, idempotency, optimistic locking, correlation propagation, and metadata persistence; verify tests cover valid metadata, invalid checksum/type, unknown case, missing idempotency key, and stale version.
- [x] 4.2 Implement evidence metadata listing for a case; verify tests cover deterministic ordering, required metadata fields, lineage/correlation fields, and unknown-case not found behavior.
- [x] 4.3 Emit evidence metadata timeline and audit records for accepted metadata registration; verify service/repository tests prove accepted metadata cannot be returned without required audit linkage.
- [x] 4.4 Ensure Phase 002 evidence metadata behavior does not invoke AI document analysis, object-storage upload orchestration, or LangGraph evidence gates; verify architecture-boundary tests cover the absence of those calls.

## 5. Timeline and Audit Baseline

- [x] 5.1 Implement `GET /api/v1/cases/{case_id}/timeline`; verify API tests return chronological event identity, case ID, event type, timestamp, actor/source, correlation ID, and linked audit reference where available.
- [x] 5.2 Extend or confirm the business audit event contract for event ID, case ID, actor, timestamp, event type, source, correlation ID, state/version metadata, and object references; verify repository and API-level tests cover `CASE_CREATED` and evidence metadata events.
- [x] 5.3 Enforce audit write failure semantics for material Phase 002 mutations; verify forced audit failure tests show no accepted create/evidence mutation is returned without its required audit event.
- [x] 5.4 Add operational replay visibility without duplicating material business audit events; verify tests distinguish idempotency replay metadata from duplicate `CASE_CREATED` or evidence events.

## 6. Synthetic Authoritative Provider Contracts

- [x] 6.1 Define read-only provider interfaces and DTOs for `TransactionProvider`, `CustomerProvider`, `AccountProvider`, `MerchantProvider`, `SettlementProvider`, and `RefundProvider`; verify contract tests cover stable DTO fields, source lineage, and the absence of posting methods.
- [x] 6.2 Add synthetic duplicate-card fixture data for customer, account, transaction, merchant, settlement, and refund context; verify provider tests return deterministic facts and source versions or response hashes.
- [x] 6.3 Persist provider context lineage for Phase 002 case creation/validation; verify case retrieval exposes provider name, source record reference, retrieval timestamp, correlation ID, normalized facts, and source version or response hash.
- [x] 6.4 Add denial/unavailability tests for refund, credit, debit, chargeback, and settlement-posting actions through Phase 002 providers and Case API; verify no financial side effect surface exists.

## 7. Architecture Boundary and Resilience Tests

- [x] 7.1 Add architecture-boundary tests proving create/retrieve/list/search/timeline/evidence metadata operations do not start LangGraph runs or checkpoints; verify tests fail if workflow runtime is invoked.
- [x] 7.2 Add architecture-boundary tests proving Phase 002 behavior does not invoke LLM, Model Gateway, RAG, recommendation, communication, HITL, or AI classification code paths; verify operations still succeed with AI disabled.
- [x] 7.3 Add persistence-authority tests proving case, evidence metadata, provider context, idempotency, timeline, and audit records are read from durable operational/audit repositories and not Redis; verify Redis is not required for the exit-gate smoke.
- [x] 7.4 Add structured error contract tests for validation, idempotency conflict, optimistic-lock conflict, not found, unauthorized/forbidden where available, and audit persistence failure; verify each includes a stable error code and correlation ID.

## 8. Documentation, Smoke Tests, and OpenSpec Validation

- [x] 8.1 Update README/runbook and any API smoke scripts for the Phase 002 canonical `/api/v1/cases` flow; verify documentation includes create, validation failure, idempotent replay, conflict replay, retrieve, list/search, timeline, evidence metadata, provider lineage, and audit checks.
- [x] 8.2 Update frontend/API client only if needed to keep the existing manual validation path aligned with canonical Case API; verify frontend lint/tests/build pass when frontend files are changed.
- [x] 8.3 Run backend `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest` from `backend/`; verify all Phase 002 unit, contract, repository, migration, API, audit, idempotency, optimistic-lock, provider, and architecture-boundary tests pass.
- [x] 8.4 Run a synthetic duplicate-card API smoke proving `created -> validated -> persisted -> retrieved -> safely replayed -> audited` without LangGraph or LLM; verify output records case ID, state version, correlation ID, provider lineage, timeline events, and audit events.
- [x] 8.5 Run `npx.cmd -y @fission-ai/openspec@1.10.0 validate --changes "002-case-api-persistence" --strict` and `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`; verify strict validation passes before requesting implementation review.
