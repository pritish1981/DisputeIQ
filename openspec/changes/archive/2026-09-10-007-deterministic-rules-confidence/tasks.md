## 1. Contracts, configuration and persistence

- [x] 1.1 Confirm approval of proposal/specs/design, including synthetic fixture parameters and Phase 008 handoff boundary; verify the approval record and FRD v3.1 traceability before code (FR-EVD-002, FR-RUL-004, FR-CNF-001).
- [x] 1.2 Add typed evidence contracts, applicability profiles, rule definitions/outcomes, confidence configuration, evaluation bundle and review-request schemas; verify schema tests reject unknown handlers, invalid ranges, timestamps, empty profiles and client-computed overrides (FR-EVD-002/003, FR-RUL-002/004, FR-CNF-001/002; Invalid registry content is rejected).
- [x] 1.3 Add canonical input hashing and immutable snapshot contracts; verify reordered equivalent inputs hash identically while changes to facts, evidence, time or versions change the hash, with nonfinite/naive inputs rejected (FR-AUD-003/004; Immutable evaluation bundle and controlled re-evaluation).
- [x] 1.4 Add additive Alembic migration, models and repositories for version/configuration, stage evaluations and durable requests; verify upgrade against current live PostgreSQL head, uniqueness, foreign-key scoping and preservation of existing cases/checkpoints (FR-ARC-011, FR-WFL-002; Existing checkpoint compatibility).
- [x] 1.5 Add reviewed JSON synthetic profiles and controlled registry loader with environment, approval/hash and regression evidence validation; verify same-version mutation, ambiguous selection, missing version and failed-regression activation are rejected (FR-RUL-004/005; Governed rule registry and rule-set versions).

## 2. Authoritative context and evidence completeness

- [x] 2.1 Extend read-only provider fixtures/context acquisition for the candidate transaction and both settlement/refund records with source-as-of timestamps; verify missing candidate, same-ID, timeout, stale snapshot and record lineage cases without deriving facts from possible_duplicate_ref alone (FR-ARC-002, FR-RUL-001; Possible duplicate reference is insufficient).
- [x] 2.2 Implement profile selection and deterministic checklist satisfaction/weighted completeness with a separate mandatory gate; verify full, partial, optional, duplicate-upload, unrelated-upload and invalid-profile cases (FR-EVD-002/003; Versioned evidence contract evaluation).
- [x] 2.3 Implement freshness, validation-unknown and same-record conflict predicates with stable reasons; verify age boundary, future/missing source time, unavailable validation and contradictory authoritative facts, keeping valid pair nonmatches distinct (FR-EVD-003/005; Evidence freshness and conflict reasons).
- [x] 2.4 Persist evidence assessments and evidence requests with evaluation lineage; verify repeat evaluation does not duplicate requests and new evidence creates linked reassessment before continuation (FR-EVD-004; Durable evidence request and reassessment).

## 3. Deterministic policy applicability

- [x] 3.1 Formalize a shared eligibility service and versioned dispute/policy-family mappings over existing SQL metadata predicates; verify missing mappings and boundary effective dates abstain or select correctly (FR-POL-003, FR-ARC-004; Versioned applicability decision record).
- [x] 3.2 Constrain both PostgreSQL FTS and pgvector branches to the same eligible set and persist eligibility reasons; verify live SQL excludes wrong product/channel/jurisdiction/dispute family and inactive, unapproved or ineffective content (FR-POL-003; Both search branches use the eligible set).
- [x] 3.3 Persist exact admitted policy/citation lineage and validate profile compatibility, revocation and integrity before new progression; verify corpus promotion preserves historical replay and explicit re-resolution creates new lineage (FR-POL-005/008, FR-AUD-003/004; Pinned admitted policy context).

## 4. Rules Engine and disposition candidate

- [x] 4.1 Implement pure registry-selected rule dispatch with stable ordering and complete result records; verify identical pinned inputs yield identical outputs and handlers cannot call models/providers or mutate case state (FR-RUL-001/002, FR-ARC-005; Rule exceptions and execution lineage).
- [x] 4.2 Implement ownership/card eligibility, configured timeline and evidence/policy gate rules; verify accepted/adverse outcomes and exact filing-limit boundaries with independently specified golden expectations (FR-RUL-001/004; Timeline boundaries are reproducible).
- [x] 4.3 Implement paired transaction identity/account/merchant/currency/Decimal amount/time and remediation rules plus versioned disposition reduction; verify matched, nonmatched, same-ID, missing candidate, fully/partly refunded, pending and conflicting fixtures (FR-RUL-001; Deterministic duplicate-card evaluation).
- [x] 4.4 Persist rule executions with facts hash and individual rule/policy/version/reason references; verify INDETERMINATE/ERROR create REVIEW_REQUIRED and durable manual requests without LLM fallback (FR-RUL-002/003; UC-EXC-007).

## 5. Governed confidence

- [x] 5.1 Implement pinned signal extraction/normalization, Decimal weighted computation, penalties, rounding and factor provenance using reviewed synthetic config; verify independently calculated expected aggregates including determinate FAIL certainty and absent/out-of-range signals (FR-CNF-001/002/004; Versioned explainable confidence computation).
- [x] 5.2 Implement mandatory gates and minimum-threshold comparison with durable supervisor/manual requests; verify high scores never bypass gates, equality passes only readiness and below-threshold/unknown config pauses (FR-CNF-003, FR-ARC-006; Hard gates precede confidence readiness, UC-EXC-008).
- [x] 5.3 Persist explainable confidence evaluations linked to rule/evidence/policy results; verify threshold activation does not rewrite old results and explicit new-version evaluation retains prior lineage (FR-CNF-004, FR-AUD-003; Threshold update preserves earlier evaluation).

## 6. Workflow, transaction safety and read visibility

- [x] 6.1 Register an explicit Phase 007 graph version and wire profile/context, evidence, policy, rules and confidence stages; verify supported duplicate-card reaches CONTROLLED_STOP/deterministic_disposition_ready and all failed gates stop downstream execution (FR-WFL-001, FR-ARC-001..006; Phase 007 deterministic progression).
- [x] 6.2 Extend typed waiting states/checkpoint references and persist result/request/audit atomically using the outer workflow transaction; verify request/checkpoint/audit write failure rolls back accepted progression (FR-WFL-002/004, FR-AUD-001; Review persistence fails).
- [x] 6.3 Add explicit linked re-evaluation to authorized version-checked resume with immutable bundles and idempotency; verify process restart, concurrent/stale resume, changed inputs, retry reuse and forged approval rejection (FR-WFL-005, FR-ARC-012; Immutable evaluation bundle and controlled re-evaluation).
- [x] 6.4 Preserve historical graph readers/semantics and reject unknown versions; verify old checkpoints remain readable and cannot silently execute new rules, and UPI/ATM downstream remains outside this graph (FR-WFL-002; Existing checkpoint compatibility).
- [x] 6.5 Add scoped control-evaluation list/detail APIs and typed frontend client; verify successful history/detail, unknown/cross-workflow IDs, validation errors and absence of raw sensitive payloads (FR-CNF-004, FR-RUL-003; Authorized control evaluation visibility).
- [x] 6.6 Add focused React evaluation details with checklist, deterministic findings, confidence contributions, gates and pinned versions; verify UI component tests and manual browser inspection show deterministic outputs separately from AI classification with no approval/posting actions (FR-RUL-003, FR-CNF-004; Rule result is distinguishable from AI rationale).
- [x] 6.7 Add correlated control audit/telemetry events; verify every accepted stage/request/re-evaluation has lineage and retries emit no duplicate material events or sensitive logs (FR-AUD-001..004, FR-OBS-001/002; Deterministic control audit lineage, Correlated control telemetry).

## 7. Integrated acceptance and runbook

- [x] 7.1 Add a versioned controls golden dataset/evaluation command with independently specified expected results; verify happy/adverse, evidence missing/stale/conflict, eligibility exclusion, rule exception, low confidence, boundary and invalid-config scenarios all pass and failed suites block activation (FR-RUL-005, FR-OBS-005; Deterministic controls regression gate).
- [x] 7.2 Add and run live PostgreSQL controls smoke through paired facts -> evidence -> eligible cited policy -> rules -> confidence -> controlled disposition candidate, including restart/replay and evidence re-evaluation; verify pinned versions/hashes, durable requests and no duplicate side effects (Phase 007 exit; UC-E2E-001 deterministic prefix, UC-EXC-005..008).
- [x] 7.3 Run backend Ruff, mypy, pytest and applicable existing classification/RAG/workflow regression commands; verify controls make no direct model/posting calls and SQL filtering remains database-backed, recording exact results (FR-RUL-005, FR-OBS-005, FR-ARC-004/005/007).
- [x] 7.4 Run frontend lint, typecheck, tests and build plus browser evaluation-detail validation; record results and any access-model limitations (FR-RUL-003, FR-CNF-004).
- [x] 7.5 Run `npx.cmd -y @fission-ai/openspec@1.10.0 validate 007-deterministic-rules-confidence --strict` and `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`; record scoped and repository-wide results separately and report unrelated failures (FR-OBS-005).
- [x] 7.6 Update README with exact checkout-aware migration/fixture/smoke/API/UI commands, expected exit and review statuses, synthetic parameter limitations and observed validation evidence; verify commands match the implemented interfaces and report files changed, risks and deviations (Phase 007 acceptance; FR-AUD-003/004).

## Completion evidence

All 32 tasks completed. See [validation.md](validation.md) for requirement mapping, observed checks,
implementation notes and limits. Phase 007 scoped strict validation passes; repository-wide strict
validation has one unrelated failure. User acceptance and archive/spec synchronization completed on 2026-09-10. Git publication remains outstanding.
