## 1. Gap Review and Source Alignment

- [x] 1.1 Review Phase 003 policy ingestion models, migrations, repositories, services, API, fixtures, smoke script and tests against `FR-POL-003`, `FR-POL-004`, `FR-POL-005`, `FR-POL-006`, `FR-AUD-001`, `FR-AUD-002`, `FR-AUD-003`, `FR-AUD-004`, `FR-OBS-001`, `FR-OBS-002`, `FR-OBS-005`, `FR-OBS-006` and `FR-ARC-004`; verify the review identifies reusable ingestion/index lineage and any JSON/application-side retrieval gaps.
- [x] 1.2 Confirm Phase 004 scope is controlled hybrid policy retrieval only, with LangGraph node wiring, Model Gateway LLM calls, recommendation generation, HITL task persistence, communication and financial posting out of scope; verify architecture-boundary tests or review notes name the excluded runtime paths.

## 2. Retrieval Contracts and Configuration

- [x] 2.1 Add policy retrieval request/response schemas for duplicate-card policy resolution, including effective date, product, channel, jurisdiction, dispute metadata, actor/service reference, optional case/workflow identifiers and correlation ID; verify schema tests cover valid requests and field-level validation errors.
- [x] 2.2 Add versioned retrieval configuration for lexical/vector weights, top-k, minimum confidence, ambiguity threshold, citation requirements and deterministic reranker mode; verify tests prove configuration values appear in retrieval outputs, audit and evaluation records.
- [x] 2.3 Add confidence/abstention response contracts for missing active corpus, no eligible candidates, low confidence, ambiguous near-ties and incomplete citations; verify unit tests assert each reason returns a policy-review HITL signal without approved policy context.

## 3. Deterministic Eligibility and Database Retrieval

- [x] 3.1 Implement deterministic eligibility filtering over the active promoted corpus by status, effective date, product, channel, jurisdiction and configured applicability metadata before lexical/vector scoring; verify tests prove excluded chunks are not retrieved or ranked.
- [x] 3.2 Implement PostgreSQL lexical retrieval for eligible chunks using full-text search/readiness materialization from Phase 003; verify an integration or SQL smoke test fails if retrieval uses only application-side token scoring.
- [x] 3.3 Implement pgvector similarity retrieval for eligible chunks using stored vector columns from Phase 003 and deterministic query embeddings; verify an integration or SQL smoke test fails if embeddings are stored or scored only as JSON/application-side vectors.
- [x] 3.4 Implement deterministic hybrid score fusion and rank ordering with lexical score, vector score, fused score, rank and optional deterministic reranker metadata; verify duplicate-card tests return stable ranking for repeated runs.

## 4. Citations, Confidence Gate and Audit

- [x] 4.1 Build citation-lineage reconstruction into retrieval results for document ID, version, section, chunk ID, chunk hash, effective date range, ingestion run ID, corpus version and index version; verify tests reconstruct citations without reading the original source file.
- [x] 4.2 Implement confidence and ambiguity gating after retrieval and citation validation; verify low score, near-tie ambiguity and missing-citation cases abstain and emit policy-review HITL signals.
- [x] 4.3 Emit append-only policy retrieval audit events for successful retrieval and abstention with actor/service, timestamp, source, correlation ID, corpus/index/config versions, selected citations, candidate/result counts and confidence outcome; verify audit tests cover success and abstention lineage.
- [x] 4.4 Make audit persistence part of the accepted retrieval operation boundary; verify simulated audit-write failure prevents a successful retrieval response and emits no automated continuation signal.

## 5. API, Smoke and Evaluation Surface

- [x] 5.1 Add protected read-only policy retrieval API endpoint(s) or an equivalent smoke command that exercises the same retrieval service path; verify API/smoke tests cover success, missing corpus, no candidates, low confidence, ambiguity, missing citation lineage, unauthorized caller and structured errors.
- [x] 5.2 Add synthetic duplicate-card retrieval fixtures with eligible active policy, stale/superseded similar text, wrong product/channel/jurisdiction variants and low-confidence queries; verify fixtures load through the Phase 003 ingestion/promotion path before retrieval runs.
- [x] 5.3 Add retrieval regression evaluation for quality, citation correctness, metadata filtering and stale-policy exclusion thresholds; verify passing fixtures record success and failing fixtures block retrieval configuration acceptance with structured metric details.
- [x] 5.4 Add retrieval telemetry/evaluation records for case ID when available, workflow ID when available, correlation ID, corpus version, index version, retrieval configuration version, eligible candidate count, returned result count, latency and abstention reason; verify observability tests or smoke output expose the required fields.

## 6. Documentation and Validation

- [x] 6.1 Update README/runbook with policy fixture load/promote, retrieval API or smoke execution, PostgreSQL FTS/pgvector proof queries, evaluation thresholds, confidence/abstention behavior and manual validation steps; verify commands and expected outputs are documented.
- [x] 6.2 Run backend `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest` from `backend/`; verify all policy retrieval, citation, audit, evaluation, API, migration/readiness and architecture-boundary tests pass.
- [x] 6.3 Run a synthetic Phase 004 smoke proving `promoted corpus -> deterministic eligibility -> PostgreSQL lexical search -> pgvector similarity -> fusion/rerank -> cited context -> confidence/audit/evaluation` with no LangGraph, recommendation, communication or financial posting behavior; verify output records corpus version, index version, retrieval config version, selected citations, confidence, correlation ID and audit event IDs.
- [x] 6.4 Run `npx.cmd -y @fission-ai/openspec@1.10.0 validate --changes "004-hybrid-policy-retrieval" --strict` and targeted long-lived spec validation as appropriate; verify strict validation passes before requesting implementation approval.
