## Context

See `proposal.md` for motivation. The repository is currently an initialized scaffold with long-lived OpenSpec specs, README guidance, CI placeholders, and empty implementation directories. This foundation change is the first implementation change and must establish deterministic platform behavior before LangGraph, RAG, Model Gateway, HITL, recommendation, communication, or deployment hardening are introduced.

The FRD/HLD/LLD source hierarchy requires synthetic-only data, clear state ownership, idempotent mutation where required, immutable business audit events, read-only provider interfaces for banking facts, and no autonomous financial execution.

## Goals / Non-Goals

**Goals:**

- Create a minimal but real FastAPI/Pydantic backend for synthetic dispute case creation and retrieval.
- Persist foundation business state in PostgreSQL using Alembic migrations.
- Provide deterministic intake validation before any workflow or AI processing.
- Provide idempotency behavior for create-case mutation.
- Persist and expose initial case timeline, evidence metadata references, synthetic provider context, and `CASE_CREATED` audit event.
- Provide a simple React/TypeScript UI for case creation and case detail verification.
- Establish local and CI validation commands that future changes can build on.

**Non-Goals:**

- No LangGraph runtime, graph nodes, checkpoints, interrupts, or workflow execution.
- No policy RAG, pgvector, embeddings, retrieval, reranking, or citations.
- No Model Gateway, direct LLM provider calls, AI-assisted classification, recommendation, or communication.
- No HITL decision workflow, reviewer queue, supervisor review, or resume.
- No real banking connectivity or production customer data.
- No refund, credit, debit, chargeback, or material financial posting capability.

## Decisions

### Decision: Keep foundation deterministic and non-AI

The create/retrieve path will validate, persist, enrich with synthetic provider context, and audit without invoking LangGraph or models.

Alternatives considered:
- Start LangGraph immediately: rejected because FRD sequencing and AGENTS.md reserve workflow runtime for a later approved change.
- Stub LLM classification in foundation: rejected because classification belongs to the bounded AI and Model Gateway phase.

### Decision: PostgreSQL is the durable foundation authority

Foundation case data, timeline entries, idempotency records, provider-context references, evidence metadata, and audit events will be modeled for PostgreSQL and migrated with Alembic.

Alternatives considered:
- In-memory or JSON-only persistence: rejected because the pilot must practice durable operational data and audit behavior.
- Redis-backed persistence: rejected because Redis is transient only and cannot be durable authority.

### Decision: Use explicit persistence contracts for foundation entities

The initial schema should separate cases, timeline entries, idempotency records, evidence metadata, provider context, and audit events even if they share the same local PostgreSQL database during the pilot.

Alternatives considered:
- One large JSON case row: rejected because it obscures auditability, indexing, idempotency, and future workflow integration.
- Fully separate physical databases in Week 1: deferred because logical separation is enough for local foundation learning and avoids premature operations overhead.

### Decision: Synthetic providers are read-only adapters

Synthetic customer/account/transaction context will be returned through allow-listed read-only provider interfaces and persisted with source lineage.

Alternatives considered:
- Hard-code provider facts inside case service: rejected because it hides the authoritative-provider boundary.
- Add write-capable mock banking tools: rejected because financial posting is out of scope and unsafe for the foundation.

### Decision: Idempotency uses key plus request fingerprint

Mutating create-case requests will store the idempotency key, request fingerprint, response reference, status, and correlation metadata. Replays with the same logical request return the original result; reuse with a different fingerprint fails.

Alternatives considered:
- Key-only idempotency: rejected because it cannot detect accidental key reuse for different payloads.
- No idempotency until workflow phase: rejected because FR-CAS-004 requires mutating APIs to support safe replay.

### Decision: CI remains scaffold-aware but becomes real when package files exist

Backend and frontend workflows can retain scaffold checks, but this change should add actual project commands and documentation once `pyproject.toml` and `package.json` exist.

Alternatives considered:
- Defer CI until later: rejected because testing starts in Sprint 1.
- Add all future workflows now: deferred because graph, RAG, AI, and deployment workflows should land with their behavior changes.

## Component Classification

- FastAPI case API: deterministic application component.
- Case service: deterministic business service.
- Idempotency service: deterministic platform/business control.
- Synthetic providers: tool/adapter components, read-only.
- Audit service: deterministic platform governance component.
- React UI: human-facing application component.
- PostgreSQL/Alembic: platform persistence.
- Redis: not used as durable authority in this change.
- LangGraph, Model Gateway, RAG, HITL, recommendation, communication: explicitly excluded until later changes.

## State Ownership and Data Contracts

- `cases`: durable business case identity, intake fields, status, timestamps, and correlation metadata.
- `idempotency_records`: mutation replay control keyed by operation, key, and request fingerprint.
- `timeline_entries`: chronological case-visible events.
- `evidence_metadata`: metadata references only; no large evidence bytes in relational rows.
- `provider_context`: source-lined synthetic facts and response hashes/versions.
- `audit_events`: append-only business audit events independent of application logs.

Every persisted record created from an inbound request should include or link to `case_id` and `correlation_id` where applicable.

## Failure Handling

- Invalid intake returns field-specific validation errors and does not create a case.
- Idempotency replay with matching fingerprint returns the original result.
- Idempotency conflict with mismatched fingerprint fails without creating a new case.
- Synthetic provider lookup failures are classified and persisted as safe foundation context errors only when the case can still be represented; mandatory missing transaction context should prevent accepted creation unless explicitly configured otherwise.
- Audit write failure blocks successful case creation because `CASE_CREATED` is a material audit event for the foundation.

## Security, Audit, and Observability

- Use synthetic-only fixtures and avoid secrets in source, logs, prompts, or config.
- Validate all public request schemas with Pydantic.
- Preserve correlation ID across API response, case records, provider context, timeline, and audit events.
- Emit structured logs without sensitive payload bodies by default.
- Keep audit records append-only at the service/repository boundary.

## Migration Plan

1. Add backend/frontend package configuration and implementation files.
2. Add Alembic foundation migration for business and audit tables.
3. Run migration against local PostgreSQL.
4. Run backend lint/type/test checks.
5. Run frontend lint/test/build checks.
6. Run API smoke checks for create, idempotent replay, retrieval, validation error, and idempotency conflict.

Rollback approach for local pilot:
- Drop or reverse the foundation Alembic migration in development environments only.
- Preserve migration history once merged; use forward-fix migrations after review.

## Risks / Trade-offs

- Foundation scope creep into LangGraph or AI -> Keep explicit non-goals in tasks and tests.
- Over-modeling the database too early -> Use separate contracts but minimal fields required by FRD/HLD/LLD.
- False confidence from SQLite-only tests -> Use SQLite only for fast unit/integration tests where appropriate and keep PostgreSQL smoke/migration checks documented.
- Provider fixture realism too low -> Include enough synthetic source lineage to exercise downstream audit and context boundaries.
- CI failures due missing local tools -> Document exact commands and keep scaffold-aware checks until package files are added.
