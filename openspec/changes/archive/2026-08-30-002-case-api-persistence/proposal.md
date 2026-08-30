## Why

FRD v3.1 separates case API and persistence from the prior platform-foundation bundle so the durable case domain can become a clear, testable contract before LangGraph, RAG, rules, recommendation, or LLM runtime behavior is introduced. This change establishes the Phase 002 baseline required for `UC-E2E-001` and the FRD Phase 002 exit gate: a synthetic duplicate-card dispute can be created, validated, persisted, retrieved, safely replayed, and audited without LangGraph or an LLM.

## What Changes

- Add the Phase 002 case-domain contract for case identity, lifecycle status, transaction/customer/account/channel references, timestamps, channel metadata, evidence metadata, timeline entries, optimistic locking, and business audit lineage.
- Expose versioned Case APIs for `POST /api/v1/cases`, `GET /api/v1/cases/{case_id}`, `GET /api/v1/cases/{case_id}/timeline`, evidence metadata create/list operations, and MVP case listing/search where required for retrieval by operational metadata.
- Preserve compatibility with any existing Phase 001 dispute endpoints only as a transition surface; the Phase 002 normative API surface is `/api/v1/cases`.
- Enforce Pydantic request/response contracts, mandatory validation, idempotency-key replay, idempotency conflict detection, optimistic concurrency for case mutations, persistence boundaries, and structured error responses.
- Define synthetic authoritative provider interfaces and test doubles for `TransactionProvider`, `CustomerProvider`, `AccountProvider`, `MerchantProvider`, `SettlementProvider`, and `RefundProvider`, with read-only investigation behavior for Phase 002 and no autonomous financial posting.
- Persist append-only baseline business audit events and chronological timeline records for material case actions, including case creation and evidence metadata registration.
- Keep LangGraph orchestration, LLM/model calls, policy RAG, deterministic rules execution, confidence scoring, HITL decisions, communications, and refund/settlement posting out of scope for this change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `case-intake-and-management`: Refine Phase 002 case entity, lifecycle, status, create/retrieve/list/search, timeline, idempotency, optimistic locking, and duplicate-card replay behavior for `FR-CAS-001` through `FR-CAS-005`.
- `api-integrations`: Define the versioned `/api/v1/cases` API contracts, Pydantic request/response schemas, idempotency headers, optimistic-lock headers, structured errors, and MVP provider-interface contract expectations.
- `authoritative-context`: Add Phase 002 synthetic authoritative provider contracts and test-double behavior for transaction, customer, account, merchant, settlement, and refund context with source lineage under `FR-CTX-001` through `FR-CTX-005`.
- `evidence-management`: Add evidence metadata API behavior and persistence baseline for evidence registration/listing without full document analysis, object upload orchestration, LangGraph gates, or AI-assisted extraction under `FR-EVD-001` through `FR-EVD-003`.
- `audit-governance`: Add baseline append-only audit persistence and audit event contract coverage for case creation, idempotent replay visibility, evidence metadata registration, timeline linkage, and correlation under `FR-AUD-001` and `FR-AUD-002`.
- `architecture-flow-controls`: Preserve Phase 002 boundaries that prohibit LangGraph execution, LLM/model invocation, RAG, recommendation, autonomous financial posting, and Redis-as-durable-authority for the case API and persistence surface.

## Impact

- Backend FastAPI routes, Pydantic schemas, domain services, repository interfaces, SQLAlchemy models, Alembic migrations, synthetic provider adapters/test doubles, audit persistence, and error handling.
- Backend unit, contract, migration, repository, API integration, idempotency/replay, optimistic-lock, audit, and architecture-boundary tests.
- Frontend/API client and README/runbook updates only where needed to align with the canonical Phase 002 `/api/v1/cases` surface and validation evidence.
- OpenAPI output and operational documentation for the case API, evidence metadata API, timeline endpoint, and synthetic provider contract behavior.
- No new runtime dependency on LangGraph, LLM providers, pgvector/RAG retrieval, object-storage binary upload, HITL workflow, communications, or financial posting adapters.
