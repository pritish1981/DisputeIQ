## 1. Backend Project Foundation

- [x] 1.1 Create the backend Python 3.12 project configuration with FastAPI, Pydantic v2, SQLAlchemy/Alembic, Ruff, mypy, pytest, and verify `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest` can execute from `backend/`.
- [x] 1.2 Add backend application bootstrap, settings, database session management, and health endpoint, and verify the health endpoint test passes.
- [x] 1.3 Define Pydantic request/response schemas for foundation case creation and retrieval mapped to FR-CAS-001, FR-CAS-002, FR-CAS-004, FR-CAS-005, and verify schema unit tests cover valid and invalid payloads.

## 2. Persistence and Migration

- [x] 2.1 Add Alembic configuration and the foundation migration for cases, idempotency records, timeline entries, evidence metadata, provider context, and audit events, and verify migration upgrade succeeds against local PostgreSQL.
- [x] 2.2 Implement repository contracts for case, idempotency, timeline, provider context, evidence metadata, and audit records, and verify repository tests cover create/retrieve and append-only audit behavior.
- [x] 2.3 Add indexes and uniqueness constraints for case identifiers, idempotency operation/key/fingerprint, timeline ordering, and audit event identifiers, and verify constraint tests cover duplicate and conflict scenarios.

## 3. Case Intake and Idempotency

- [x] 3.1 Implement deterministic mandatory intake validation before workflow or AI execution, and verify missing-field API tests return structured field-level validation errors with no case created.
- [x] 3.2 Implement create-case service behavior for accepted synthetic duplicate-card disputes, and verify the response includes case ID, `Submitted` status, correlation ID, and created timestamp.
- [x] 3.3 Implement idempotent create-case replay for matching idempotency key and request fingerprint, and verify replay returns the original result without creating a second case.
- [x] 3.4 Implement idempotency conflict handling for reused keys with different payloads, and verify the API rejects the request without creating a second case.
- [x] 3.5 Implement case retrieval with timeline, evidence metadata, provider context, and audit visibility, and verify case detail integration tests cover the full foundation response.

## 4. Synthetic Provider Context

- [x] 4.1 Define read-only synthetic customer, account, and transaction provider interfaces for foundation context capture, and verify contract tests prohibit write/posting operations.
- [x] 4.2 Add synthetic fixture data for a duplicate-card transaction case, and verify fixture tests return stable customer/account/transaction facts.
- [x] 4.3 Persist source lineage for synthetic provider context including provider name, source record reference, retrieval timestamp, correlation ID, and response hash or version where feasible, and verify retrieval exposes the lineage.

## 5. Audit, Timeline, and Correlation

- [x] 5.1 Implement correlation ID accept/generate behavior for inbound foundation API requests, and verify tests cover supplied and generated correlation IDs.
- [x] 5.2 Emit `CASE_CREATED` as an append-only business audit event independent of application logs, and verify audit tests include case ID, event type, actor, source, timestamp, and correlation ID.
- [x] 5.3 Create a chronological timeline entry for case creation linked to the audit event, and verify case detail returns timeline entries in order.
- [x] 5.4 Ensure audit write failure blocks successful case creation, and verify a failure-path test proves no accepted case is returned without the required audit event.

## 6. Frontend Foundation UI

- [x] 6.1 Create the React/TypeScript project configuration and API client, and verify frontend install, lint, tests, and build commands pass.
- [x] 6.2 Implement a minimal case creation screen for synthetic duplicate-card intake, and verify component tests cover required-field validation and successful submit rendering.
- [x] 6.3 Implement a case detail/status view showing status, timeline, evidence metadata, provider context, audit events, and correlation ID, and verify UI tests cover rendered foundation fields.
- [x] 6.4 Add a manual UI validation checklist to project documentation, and verify it covers create, idempotent replay, retrieve, validation failure, and case detail review.

## 7. Architecture Boundary Tests

- [x] 7.1 Add tests proving foundation case creation does not start LangGraph workflow execution, and verify no workflow run/checkpoint is created by this change.
- [x] 7.2 Add tests proving foundation case creation does not invoke an LLM, Model Gateway, policy RAG, recommendation, communication, or HITL decision workflow.
- [x] 7.3 Add tests proving no refund, credit, debit, chargeback, or material financial posting API/provider interface is exposed in the foundation surface.
- [x] 7.4 Verify Redis is not used as durable authority for foundation business records by documenting and testing that durable records are read from PostgreSQL-backed repositories.

## 8. CI, Documentation, and Validation

- [x] 8.1 Update backend GitHub Actions to run the real backend lint/type/test commands when backend project files exist, and verify workflow syntax remains valid.
- [x] 8.2 Update frontend GitHub Actions to run the real frontend lint/test/build commands when frontend project files exist, and verify workflow syntax remains valid.
- [x] 8.3 Keep OpenSpec and security baseline workflows aligned with this change, and verify they reference only available foundation checks.
- [x] 8.4 Update README/runbook documentation with local startup, migration, backend checks, frontend checks, API smoke checks, and expected synthetic outputs.
- [x] 8.5 Run final local validation for this change: backend checks, frontend checks, PostgreSQL migration, API smoke for create/replay/retrieve/validation/conflict, and OpenSpec strict validation when the CLI is available.
