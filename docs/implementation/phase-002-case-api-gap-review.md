# Phase 002 Case API and Persistence Gap Review

This review maps the approved `002-case-api-persistence` OpenSpec change to the Phase 001
implementation. The governing program document is
`docs/source-of-truth/DisputeIQ_FRD_v3.1.docx`; the older v3.0 filename still present in
some repository guidance is not present in this checkout.

## Requirements Traceability

| Requirement | Phase 001 reuse | Phase 002 implementation and verification |
| --- | --- | --- |
| FR-CAS-001 | Case ID, core references, submitted timestamp, PostgreSQL model | Channel metadata, opened/closed timestamps, state version, canonical create/retrieve responses; repository, service, and API tests |
| FR-CAS-002 | Pydantic mandatory fields | Reference formats, duplicate-card-only gate, field-level common error envelope, no-side-effect validation tests |
| FR-CAS-003 | Submitted status | Explicit lifecycle constants and transition validation, monotonic aggregate version |
| FR-CAS-004 | Create idempotency key and payload fingerprint | Canonical operation scope, replay counters, conflict isolation, evidence idempotency, optimistic locking |
| FR-CAS-005 | Embedded timeline | Dedicated chronological timeline endpoint plus deterministic search/listing |
| FR-EVD-001..003 | Inline file metadata persisted at creation | Evidence type/object/source/status/lineage fields, create/list endpoints, deterministic metadata-only behavior |
| FR-CTX-001..005 | Customer, account, transaction synthetic context | Read-only customer/account/transaction/merchant/settlement/refund contracts, fixtures, hashes, source versions, persisted lineage |
| FR-AUD-001..002 | Append-only CASE_CREATED record | State-versioned case/evidence events, linked timeline records, replay visibility, audit-failure rollback |
| FR-ARC-001/003/005/009/011/012 | No AI or posting dependencies in foundation | Boundary tests cover no LangGraph, LLM, RAG, HITL, communication, Redis authority, or financial posting surface |

## API Transition

`/api/v1/cases` is the canonical Phase 002 surface. `POST /api/v1/disputes` and
`GET /api/v1/disputes/{case_id}` remain deprecated compatibility routes and delegate to
the same Case Service, persistence, idempotency operation, validation, and audit behavior.
They do not maintain a separate dispute aggregate.

Phase 002 inherits the pilot's single synthetic-data access assumption; tenant/role
authorization is not introduced by this change. Unknown resources, unsupported filters,
provider write attempts, and all available control failures use the common error contract
without returning unrelated case data.

## Deliberate Phase Boundary

The implementation stores evidence metadata but does not upload or analyze document
binaries. It resolves synthetic read-only banking facts but exposes no refund, credit,
debit, chargeback, settlement-posting, or payment command. Case operations do not start
LangGraph, checkpoints, model calls, RAG, recommendations, communications, or HITL.
