# DisputeIQ 8-Week OpenSpec Delivery Roadmap

The target is a production-style pilot, not a real bank-production deployment.

| Week | Planned OpenSpec change | Primary outcome | Exit gate |
|---|---|---|---|
| 1 | 001-platform-foundation | API, DB, case model, synthetic providers, audit, CI baseline | Create/retrieve/audit a synthetic case with no LLM |
| 2 | 002-policy-rag | Approved policy ingestion, metadata, pgvector, filtering, retrieval, citations, RAG evaluation | Retrieval/citation baseline passes |
| 3 | 003-langgraph-orchestration | Typed 11-stage graph, checkpoints, gates, retry/error taxonomy | Duplicate-card happy path traverses graph with stubbed capabilities |
| 4 | 004-ai-capabilities-and-tools | Model Gateway, classification, evidence analysis, recommendation, communication; read-only provider tooling | Structured-output and tool-boundary tests pass |
| 5 | 005-rules-confidence-hitl | Deterministic evidence gate/rules, governed confidence, HITL task/review/resume | Duplicate-card case reaches governed human decision |
| 6 | 006-security-audit-communication | RBAC, PII/injection defenses, audit reconstruction, approved communication | No material outcome without human authority |
| 7 | 007-observability-evaluation | OTel, LangSmith/LangWatch, evaluation corpus, GitHub AI/security gates | Required quality and security gates run |
| 8 | 008-expand-deploy-harden | Add UPI + ATM variants, staging deployment, resilience/E2E/hardening | All three MVP use cases pass end-to-end pilot gates |

## Scope-control rule

Do not start the next weekly change until the current change's exit gate passes or an explicit exception is recorded.

## First vertical slice

Duplicate Card Transaction is the first full end-to-end implementation. Failed UPI and ATM debit-without-cash should reuse the established orchestration and vary primarily through evidence, policy and deterministic-rule configuration.
