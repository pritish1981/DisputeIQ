## Context

See `proposal.md` for motivation. FRD v3.1, HLD v1.0, LLD v1.0, and the tech-stack note split Phase 002 into a durable Case API and persistence baseline before workflow orchestration. The current codebase already contains foundation pieces under `backend/app` and tests for `/api/v1/disputes`; implementation should reuse or adapt those pieces where they satisfy the new contract, while making `/api/v1/cases` the normative Phase 002 surface.

Phase 002 must remain deterministic and pre-orchestration. PostgreSQL-backed operational persistence and append-only business audit records own case state. Redis, LangGraph checkpoints, RAG stores, and model output stores do not own Phase 002 case truth.

## Goals / Non-Goals

**Goals:**

- Establish a canonical case domain with stable IDs, references, lifecycle status, timestamps, channel metadata, state version, provider lineage, evidence metadata, timeline, and audit linkage.
- Expose versioned Case APIs using Pydantic request/response contracts and OpenAPI documentation.
- Prove safe create-case replay through idempotency-key and request-fingerprint persistence.
- Add optimistic-lock controls for material mutations after case creation, especially evidence metadata registration and future lifecycle updates.
- Define read-only synthetic provider contracts/test doubles for transaction, customer, account, merchant, settlement, and refund context.
- Keep audit, timeline, and durable case persistence atomic enough that an accepted mutation cannot be returned without required audit evidence.

**Non-Goals:**

- No LangGraph runtime, workflow runs, or graph checkpoints.
- No LLM, Model Gateway, policy RAG, recommendation, classification AI, confidence scoring, HITL decisioning, communication generation, or document analysis.
- No object-storage binary upload pipeline beyond metadata/object-reference fields.
- No refund, credit, debit, settlement posting, chargeback execution, or autonomous money movement.
- No expansion beyond the synthetic duplicate-card slice except schema shapes that make future dispute types possible.

## Decisions

### Canonical `/api/v1/cases` Surface

Use `/api/v1/cases` as the normative Phase 002 API. If existing `/api/v1/disputes` routes remain, keep them as compatibility wrappers that delegate to the same service layer and are clearly documented as transitional.

Rationale: FRD v3.1 names Case API & Persistence as the phase and the LLD endpoint table uses cases as the external domain. Keeping wrappers avoids unnecessary breakage while moving the implementation toward the source-of-truth terminology.

Alternative considered: keep only `/api/v1/disputes`. Rejected because it would preserve Phase 001 naming drift and weaken FRD/OpenSpec traceability.

### Deterministic Case Service Owns Phase 002 Mutations

Implement create, retrieve, list/search, timeline retrieval, and evidence metadata registration through a deterministic Case Service and repositories. The service validates inputs, resolves synthetic provider context, writes business records, records audit/timeline entries, and commits or rolls back as one logical operation.

Rationale: This keeps case lifecycle and persistence outside LangGraph until the workflow phase is explicitly introduced.

Alternative considered: start the graph immediately after case creation. Rejected for Phase 002 because the exit gate explicitly requires success without LangGraph or LLM.

### Operational DB Is the Durable Authority

Persist case, transaction reference, customer/account/channel metadata, provider context lineage, evidence metadata, idempotency records, timeline entries, and audit events in PostgreSQL-backed repositories. Tests may use SQLite with equivalent constraints where already established, but contract/migration verification must exercise the production-style PostgreSQL schema when feasible.

Rationale: FRD/HLD/LLD separate durable business state from transient coordination and workflow checkpoints.

Alternative considered: cache-first storage or Redis-backed case records. Rejected because Redis is transient only.

### Idempotency Uses Operation, Key, and Fingerprint

Mutating endpoints require `Idempotency-Key`. Store operation name, key, logical request fingerprint, response reference/body, status, timestamps, and correlation metadata. Safe replay returns the original response without duplicate case, timeline, provider, or material audit records. Same key with different logical payload returns a conflict.

Rationale: This supports client retries and future workflow replay without relying on exactly-once delivery.

Alternative considered: key-only idempotency. Rejected because it cannot distinguish safe replay from conflicting payload reuse.

### Optimistic Locking Uses Monotonic Case Version

Cases carry a monotonic `state_version`. Mutations that change a persisted case aggregate after creation accept an `If-Match` header or equivalent expected-version field. Mismatch returns a structured conflict and leaves state unchanged.

Rationale: Phase 002 is the right place to establish the concurrency contract before HITL and workflow resume mutations add more writers.

Alternative considered: last-write-wins updates. Rejected because it hides stale analyst/client actions and weakens auditability.

### Provider Contracts Are Read-Only Test Doubles

Define explicit provider interfaces and DTOs for `TransactionProvider`, `CustomerProvider`, `AccountProvider`, `MerchantProvider`, `SettlementProvider`, and `RefundProvider`. For Phase 002, refund and settlement providers expose read-only context such as existing settlement/refund status; they do not post or execute financial actions.

Rationale: The FRD requires authoritative context from providers, but material money movement remains outside this phase and requires human approval in later phases.

Alternative considered: omit settlement/refund providers until finalization. Rejected because FRD v3.1 Phase 002 asks for the contract/test-double definitions now.

### Audit and Timeline Are Separate but Linked

Business audit events are append-only records with event ID, case ID, actor, timestamp, event type, source, correlation ID, version metadata, and object references. Timeline entries are case-facing chronological projections that link to audit events when the event is material. Audit write failure blocks a successful material mutation.

Rationale: Analysts need a readable timeline, while auditors need immutable reconstruction evidence independent of application logs.

Alternative considered: use timeline as the audit store. Rejected because timeline is a projection and may not contain the full immutable audit contract.

### Errors Use a Common Envelope

Case API failures return stable error codes, message, correlation ID, and field-level details where applicable. Planned codes include validation failed, missing idempotency key, idempotency conflict, not found, unauthorized/forbidden, optimistic-lock conflict, and audit persistence failure.

Rationale: Contract tests can assert behavior consistently, and operational tooling can classify failures.

Alternative considered: rely on default framework error shapes. Rejected because source-of-truth documents require machine-readable contracts and audit/correlation traceability.

## Risks / Trade-offs

- Existing Phase 001 code already implemented some now-Phase-002 behavior -> Mitigation: perform a gap review first, reuse compliant code, and avoid rewriting working persistence without a contract reason.
- API naming drift between `/disputes` and `/cases` -> Mitigation: introduce `/api/v1/cases` as canonical and keep any `/disputes` compatibility behavior thin and tested if retained.
- Evidence metadata could be mistaken for full evidence analysis -> Mitigation: responses must make clear that Phase 002 stores metadata only and does not run AI document analysis or workflow evidence gates.
- Synthetic providers could accidentally expose write-like methods -> Mitigation: contract tests must assert no refund, credit, debit, chargeback, or settlement posting operation exists in Phase 002.
- Audit/timeline atomicity can be hard to prove with partial failures -> Mitigation: add failure-path repository/service tests that force audit write failure and verify no accepted mutation is returned.
- Optimistic locking may be underused until later phases -> Mitigation: require it for evidence metadata mutation now so the contract is exercised before HITL/workflow updates.

## Migration Plan

1. Review existing Phase 001 models, migrations, services, schemas, tests, and UI/API client for reusable behavior.
2. Add an Alembic migration or corrective migration only for gaps between existing schema and Phase 002 contracts, especially `state_version`, provider breadth, evidence metadata registration fields, audit contract fields, search indexes, and unique idempotency constraints.
3. Introduce canonical `/api/v1/cases` routes and route tests; retain `/api/v1/disputes` wrappers only if they delegate to the same contracts.
4. Backfill or fixture-load synthetic duplicate-card provider records for customer, account, transaction, merchant, settlement, and refund context.
5. Run backend lint/type/unit/integration/contract/migration checks, OpenAPI contract checks, synthetic API smoke create/replay/retrieve/timeline/evidence/list/search checks, and OpenSpec strict validation.

Rollback strategy: because Phase 002 is pre-production synthetic-only, rollback is a normal code and migration rollback to the prior Phase 001 schema. If a compatibility wrapper was added, it can remain during rollback as long as it does not expose unsupported mutation semantics.

## Open Questions

- Whether the frontend should be updated in this phase beyond API-client/runbook alignment can be decided during implementation after backend scope is reviewed; it does not change the backend contract.
