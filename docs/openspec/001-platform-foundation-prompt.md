# Week 1 - OpenSpec Proposal Prompt

Use this in Codex after OpenSpec/Codex integration has been initialized.

```text
$openspec-propose

Create change: 001-platform-foundation

Program source of truth:
docs/source-of-truth/DisputeIQ_FRD_v3.0_8Week_OpenSpec_GWT_Reference_TOC_Fixed.docx

Goal:
Establish the deterministic platform foundation for DisputeIQ. This change must contain no LLM, RAG, or LangGraph runtime dependency.

Scope:
- Repository/application conventions
- Python 3.12 FastAPI backend skeleton
- Pydantic API/domain contracts
- PostgreSQL operational database
- Database migration setup
- Case lifecycle model
- Create and retrieve dispute APIs
- Case timeline baseline
- Evidence metadata baseline
- Synthetic customer/account/transaction fixtures
- Read-only provider interfaces and mock provider implementations
- Append-only business audit-event contract
- CASE_CREATED audit event
- Correlation ID and idempotency baseline
- React + TypeScript frontend shell for create/view case
- Docker Compose local PostgreSQL and Redis
- GitHub Actions baseline for OpenSpec validation, backend, frontend and security

Relevant capabilities:
- case-intake-and-management
- authoritative-context
- audit-governance
- api-integrations
- architecture-flow-controls

Relevant FRD requirements:
- FR-CAS-001 through FR-CAS-005
- FR-CTX-001 through FR-CTX-005 as applicable to provider contracts
- FR-AUD-001 and FR-AUD-002
- FR-ARC-001, FR-ARC-002, FR-ARC-011, FR-ARC-012

Non-goals:
- LangGraph workflow execution
- LLM or Model Gateway implementation
- RAG/pgvector retrieval
- classification AI
- deterministic dispute decision rules
- human review workflow
- customer communication generation
- cloud deployment

Required exit gate:
A synthetic duplicate-card dispute can be created, persisted, retrieved and displayed; provider/context contracts exist; CASE_CREATED is auditable; correlation/idempotency behavior is tested; no LLM or LangGraph runtime is required.

Requirements:
- Every spec behavior must use Given/When/Then scenarios.
- Map tasks to FRD and OpenSpec requirement IDs.
- Include unit/integration/contract tests.
- Do not implement code during proposal generation.
```
