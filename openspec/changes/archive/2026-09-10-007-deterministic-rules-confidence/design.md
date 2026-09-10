## Context

See proposal.md for motivation and scope. Phase 006 is archived at `openspec/changes/archive/2026-09-06-006-model-gateway-classification`. Current `workflow_graph.py` routes evidence -> policy -> controlled stop; its evidence gate accepts any nonempty metadata list. `synthetic_providers.py` supplies a possible duplicate reference but no second transaction record. Policy repositories already filter approval/status, effective dates, product, channel and jurisdiction before PostgreSQL FTS/pgvector scoring. Preserve this SQL path.

### Design Reconciliation / Decision Required

- **Resolved by user:** FRD v3.1 is authoritative for this change despite the stale v3.0 filename in AGENTS.md and OpenSpec configuration. Record the decision here; do not alter the FRD.
- **Phase allocation:** the FRD Phase 007 delivery table explicitly includes evidence completeness and deterministic policy eligibility. Keep its canonical change ID `007-deterministic-rules-confidence` and use the expanded display title. Older roadmap/HLD phase numbering does not replace this delivery table.
- **Exit boundary:** the detailed Phase 007 table ends at repeatable deterministic outputs and confidence; grounded recommendation and authorized human decision belong to Phase 008. UC-E2E-001 includes later stages, so this change proves its deterministic prefix and hands off a disposition candidate. It does not claim the entire use case is complete.
- **Evidence before RAG:** resolve the versioned control profile from authoritative metadata at context capture. It defines the evidence contract and compatible policy/rule families before the evidence gate; semantic retrieval cannot define mandatory evidence. After retrieval, verify exact selected policy versions against the profile. A mismatch requires review.
- **Governance values:** source documents assign ownership but do not supply bank-approved evidence ages, duplicate time windows, weights or numerical thresholds (LLD ADR-009 is explicitly a governance decision). The concrete values below are proposed synthetic pilot fixtures for review with this plan, not extracted bank policy. Production activation requires a separately approved configuration and evidence-backed calibration.

## Goals / Non-Goals

**Goals:** pure repeatable evaluation, immutable lineage, explicit failures, and a small observable duplicate-card path. Preserve source ownership and stable historical results across retries and configuration changes.

**Non-Goals:** executable user-authored rule scripts, autonomous agents, interpreting policy prose into rules, banking policy invention, full HITL decision lifecycle, OCR/malware-scanning implementation, or financial execution.

## Decisions

### 1. Service ownership and module boundaries

| Component | Class | Responsibility |
| --- | --- | --- |
| Existing classification / Model Gateway | AI-assisted / platform | Validated classification and its recorded confidence; no downstream authority |
| Existing read-only providers | Tool/adapter | Both transaction records, account/merchant/settlement/refund facts and source lineage |
| Evidence Completeness Service | Deterministic | Requirements, validation/freshness/conflict assessment and completeness |
| Policy Eligibility Service | Deterministic | Applicability decisions and candidate constraints before search |
| Rules Engine / registry | Deterministic / platform | Pure versioned rule execution and controlled configuration |
| Confidence Service | Deterministic | Signal normalization, formula and mandatory escalation gates |
| Workflow service / LangGraph | Platform | Commands, atomic persistence, state routing, checkpoints and requests |
| Analyst/supervisor | Human | Future authorized review; no automated override of material decisions |

Add focused modules under `backend/app/services/` and typed contracts under `backend/app/domain/`; persistence remains in adapters. Inject pure services into workflow orchestration. No new agent framework, rule DSL, model SDK or network dependency. Static typed rule handlers plus validated data configuration are easier to audit than evaluating dynamic expressions; reject unknown handler IDs and never use eval/exec.

### 2. Immutable control bundle and data model

An evaluation bundle contains case/workflow IDs, schema/graph version, evaluation ID, explicit UTC evaluation time, case state version, normalized facts hash and provider record references/hashes/source versions, classification invocation/output reference, evidence IDs/checksums/snapshot hash, evidence-contract version/hash, eligibility profile version/hash, policy effective-as-of date, corpus/index/retrieval versions and exact citations, rule-set/member versions/hash and confidence formula/threshold version/hash.

Use canonical JSON (sorted keys and collections, Decimal monetary strings, normalized UTC instants), rejecting nonfinite numbers and naive/invalid timestamps. Hash all inputs consumed by pure evaluation including the time anchor and configuration, not just the disputed transaction. Execution IDs, audit IDs and wall-clock latency are metadata outside the deterministic result hash.

Add logical tables (final migration names may follow repository conventions):

- `control_config_versions`: kind, ID/version, environment, effective interval, validated payload/hash, approval provenance, regression evidence; immutable version content.
- `control_evaluations`: parent/re-evaluation reference, bundle, bundle hash, stage status and immutable aggregate result references.
- `evidence_assessments`, `policy_eligibility_evaluations`, `rule_executions`, `case_confidence_evaluations`: immutable inputs/references, outcomes and reason codes. Rule executions retain every individual rule result.
- `control_review_requests`: case/workflow/evaluation, type, role, reasons, required evidence items, status, correlation ID. Unique evaluation/type prevents retry duplication; fulfillment records point to the new assessment, preserving the original request.

Registry versions are loaded from reviewed, version-controlled JSON fixtures using a local controlled loader with actor/environment and successful regression-run reference. No public config mutation API in this phase. Resolve one compatible approved bundle for a new evaluation; zero or multiple matches fail closed. Never mutate payload under the same version. A new active configuration does not alter existing evaluation results.

### 3. Evidence contract and completeness semantics

Contracts are selected by dispute type, channel, product and pinned policy/rule profile. Each requirement has a stable ID, mandatory flag, allowed evidence/provider types, minimum count, accepted validation states, freshness timestamp/maximum age where applicable, deterministic conflict predicates and integer weight.

Assess metadata and validated structured facts; an uploaded filename or object reference is not proof that bytes passed checks. Record unknown/unavailable validation separately from missing evidence. Provider errors, unavailable object validation or extraction failure cannot be converted into evidence absence or a valid item. AI extraction is not added here. Synthetic validated fixtures explicitly identify their test provenance.

Return required IDs, available item references, missing IDs, stale references, invalid/unverifiable references, conflict references/reasons and per-requirement satisfaction. Available means registered/present; satisfaction additionally requires valid, fresh, nonconflicting qualifying items. One requirement earns its weight once even if duplicate uploads exist. Completeness = sum of satisfied checklist-item weights / sum of all configured checklist-item weights, including optional items when configured; empty/zero-weight/ambiguous profiles are invalid, never 100% complete. Mandatory completeness is a separate all-mandatory predicate and cannot be compensated by optional evidence.

Synthetic `duplicate-card-evidence-v1`: seven mandatory checklist items: customer statement or receipt, authoritative disputed transaction, authoritative candidate transaction, disputed settlement, candidate settlement, disputed refund status and candidate refund status (each weight 1). Document evidence has no arbitrary age expiry; status snapshots use 24-hour maximum age from authoritative snapshot-as-of timestamp relative to pinned evaluation time. Extend provider lineage to retain this timestamp separately from local retrieval time; rereading cached data must not refresh its source age. Equality at 24 hours is fresh; future timestamps or missing source time are invalid. Contradictory assertions about the same record's ownership, currency, linked transaction identity or authoritative status are blocking conflicts. Different currencies or merchants on two otherwise valid records are determinate nonmatches, not contradictions. Similar amounts alone are not an evidence conflict or duplicate finding.

### 4. Policy eligibility and replay

Factor existing applicability logic into one service shared by standalone retrieval and workflow retrieval. Preserve SQL FTS and pgvector scoring and inclusive current effective-date endpoints; add versioned supported dispute-type/policy-family mapping backed by approved structured metadata. Derive product, jurisdiction and transaction type from authoritative records/configured mappings, and channel from recorded case intake. Missing/unknown mappings abstain; no defaults guessed from prose or LLM output.

Persist eligible/excluded policy references with predicate reason codes, evaluation inputs and eligibility version. Only the eligible set enters both SQL search branches, constrained by the same corpus and metadata predicates. Pin selected citations/document and chunk hashes after retrieval. The effective-as-of date is the transaction date required by LLD node 5, not the current wall clock; ambiguous date selection blocks evaluation.

Historical replay reads the recorded admitted policy snapshot and deterministic outputs without reranking or substituting today's corpus. For new progression/re-evaluation, verify pinned policy remains authorized for use; revocation, integrity mismatch or unavailable pinned source produces policy review. Promotion alone must not rewrite historical results. Explicit policy re-resolution creates a new linked bundle, never silently reuses old rule/confidence results.

### 5. Rules and deterministic candidate

Each rule has ID/version, handler ID, execution order, effective interval, parameters, policy/config references, applicability and mandatory flag. Outcomes: PASS, FAIL, NOT_APPLICABLE, INDETERMINATE, ERROR. PASS/FAIL are determined business results; INDETERMINATE means insufficient facts; ERROR is execution/configuration failure. Preserve stable reason codes, relevant normalized fact references and execution records. Pure handlers cannot mutate case state, call models, read the clock or invoke providers.

The synthetic duplicate-card set evaluates:

1. Ownership, active card account, supported transaction type and distinct transaction identity.
2. Posted/settled status and filing timeline; a pilot fixture uses a 120-day filing limit inclusive, measured from transaction date to case submission date.
3. Mandatory evidence and cited compatible policy gates.
4. Both candidate records match account, merchant, currency and exact Decimal amount; authorization timestamps differ by at most 300 seconds inclusive. A possible-duplicate reference only triggers read-only candidate acquisition.
5. Settlement/refund outcomes for both records: unresolved/pending status is indeterminate; a fully refunded/reversed duplicate cannot yield a new refund candidate; partial or conflicting refund facts require review.

These numbers and predicates are synthetic configuration proposed for acceptance, not actual bank entitlement rules. Fixtures include matched, nonmatched, same-ID, one-record-only, already-refunded, partial-refund, pending and contradictory cases. Do not infer network transaction facts from customer claims.

Reduce complete results using a versioned disposition map: `DUPLICATE_SUPPORTED`, `DUPLICATE_NOT_SUPPORTED`, `ALREADY_REMEDIATED`, or `REVIEW_REQUIRED`. Any mandatory indeterminate/error or blocking conflict yields REVIEW_REQUIRED. Known adverse findings remain deterministic findings, not errors or low certainty. No candidate updates final case outcome or invokes money movement.

### 6. Governed confidence formula

Persist raw signal values/references, normalizations, weights, contributions, penalties, aggregate, threshold, gate reasons and formula version. Proposed synthetic `case-confidence-v1`:

`score = clamp(0.15*C + 0.30*E + 0.25*P + 0.30*R - 0.20*X - 0.20*T, 0, 1)`

- C = existing schema-valid accepted classification confidence in [0,1], retaining model/prompt provenance.
- E = deterministic completeness score in [0,1].
- P = admitted retrieval confidence in [0,1] with retrieval-config provenance; do not conflate this with semantic certainty or change existing ranking calibration.
- R = fraction of applicable rules with determinate PASS/FAIL outcomes. NOT_APPLICABLE is excluded; an empty applicable set is unknown and blocking. FAIL is not zero certainty.
- X = 1 if any unresolved contextual conflict exists, otherwise 0, with explicit conflict references.
- T = failed required provider operations / total required provider operations; an unavailable denominator is unknown. Retain error references.

Round Decimal result to six places using ROUND_HALF_UP; threshold is 0.70 inclusive for the synthetic fixture. Below threshold creates supervisor review. All raw signals are retained; missing/nonfinite/out-of-range signals yield a conservative zero diagnostic contribution and a blocking unknown-input reason (no weight redistribution). Missing/invalid formula or thresholds yields no valid score and configuration review.

Mandatory evidence failure, unaccepted classification, unapproved/uncited policy, mandatory rule indeterminacy/error, blocking conflict and required provider failure always block readiness even with a high aggregate. An adequate score permits only the next recommendation boundary. Regression datasets and a recorded governance decision must precede production thresholds; do not lower thresholds merely to make smoke pass.

### 7. Graph, requests and resume

New graph version adds rules and confidence after policy context. Context capture resolves/pins controls and acquires the second transaction plus its settlement/refund records. Evidence gates precede RAG; unresolved gates prevent downstream execution. On success, retain `CONTROLLED_STOP` with `deterministic_disposition_ready`, candidate, result references and next boundary `recommendation_and_human_decision`.

Reuse WAITING_EVIDENCE and WAITING_POLICY_REVIEW; add WAITING_RULE_REVIEW and WAITING_SUPERVISOR_REVIEW, with typed configuration-error reasons on the appropriate controlled review path. Store a durable REQUEST_ADDITIONAL_EVIDENCE, MANUAL_REVIEW or SUPERVISOR_REVIEW request as needed; missing-policy requests use POLICY_REVIEW. These are internal records, not sent customer messages or completed HITL decisions.

Persist result, request, checkpoint, idempotency and audit in the same accepted transaction. Pure evaluation is separate from persistence. Services called inside WorkflowService use its session with no commits. Failure to persist audit/checkpoint rolls back the accepted state transition. Unique evaluation/stage keys plus optimistic version checks prevent concurrent resumes from duplicating records.

Existing start/detail/resume remains supported. New evaluation is selected by an explicit registered graph version; reject unknown graph versions. Historical graph versions remain readable and retain their existing stop; never execute Phase 007 under an old version label. Evidence arrival plus authorized resume creates a linked evaluation with updated evidence/time and reruns affected downstream stages, preserving chosen control versions unless an explicit re-evaluation selects new ones. Old result bundles remain immutable. Low-confidence/rule-review requests cannot be bypassed by a client `approved=true` flag; Phase 008 reviewer adjudication is unavailable, so those requests stay paused. Re-evaluation is for changed validated inputs, not an approval override.

Add `GET /api/v1/workflows/{workflow_id}/control-evaluations` and `GET /api/v1/workflows/{workflow_id}/control-evaluations/{evaluation_id}` with existing actor/access conventions and workflow/case scoping. Extend resume with a typed optional re-evaluation request (reason, prior evaluation ID, retain-pins by default); conflicting idempotency payload or stale state returns 409. Caller cannot submit computed scores/rule outcomes/config payloads. Unknown or cross-workflow evaluation IDs return structured not-found/access errors.

A focused React details view reads these outputs, labels deterministic findings separately from AI classification/rationale and displays component contributions, gates and version references. No reviewer approve/refund buttons.

### 8. Audit, security and verification

Events: CONTROL_CONFIG_REGISTERED, EVIDENCE_ASSESSED, POLICY_ELIGIBILITY_EVALUATED, RULES_EXECUTED, CASE_CONFIDENCE_EVALUATED, CONTROL_REVIEW_REQUESTED and CONTROL_REEVALUATED. Include actor/service, IDs, correlation, version/hash references, reasons and stage status. Keep provider payloads, evidence binaries, secrets and prompts out of logs/checkpoints; sensitive fact snapshots stay in existing access-controlled business persistence.

Golden test expectations are independently specified in versioned fixtures; verify boundary values, adverse determinate outcomes, missing data, duplicate evidence, source conflicts, exceptions, threshold equality, unavailable versions and replay. Test actual PostgreSQL filtering and durable restart/re-evaluation, not just SQLite or mocks. Preserve existing classification, retrieval and case regression suites and assert deterministic services make zero model or posting calls. Run backend checks, frontend checks, live controls smoke, targeted OpenSpec validation and `validate --all --strict`; report unrelated pre-existing failures separately.

## Risks / Trade-offs

- Synthetic policy parameters lack bank approval -> clearly label fixtures and require approved production profile; test results establish mechanics, not real policy correctness.
- Metadata cannot establish binary safety -> retain validation unknown/unavailable states and block requirements that need unperformed validation.
- Immutable snapshots increase storage -> compact checkpoint references; preserve enough persisted inputs for reconstruction.
- Full HITL is later -> internal durable requests and safe pause now; no fabricated human authorization.
- Current normalization change overlaps main capabilities -> validate against current main specs and report separate failures; do not alter unrelated planning artifacts.

## Migration Plan

1. Add schema/contracts and migration after verifying current Alembic head; seed only explicit synthetic reviewed fixture versions in the local environment.
2. Implement pure services and golden suite; validate registry and migration with live PostgreSQL.
3. Register Phase 007 graph version and expose evaluation reads/UI; preserve old checkpoint readers and old graph semantics.
4. Run full applicable regression, SQL eligibility checks and live smoke before enabling Phase 007 for new cases.
5. Roll back by disabling new graph starts and retaining evaluation/config tables and historical records. Do not downgrade away audited results or automatically resume blocked cases under older code.
