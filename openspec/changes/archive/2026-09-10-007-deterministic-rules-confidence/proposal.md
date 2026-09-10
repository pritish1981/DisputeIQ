## Why

Phase 006 provides governed classification, but the workflow still uses a preliminary evidence-presence gate and stops after policy retrieval. Phase 007 adds **Deterministic Controls, Rules & Confidence** so a duplicate-card investigation yields repeatable, explainable disposition inputs before recommendation and human decision.

Authority: `docs/source-of-truth/DisputeIQ_FRD_v3.1.docx`, explicitly confirmed by the user for this change. Supporting sources: HLD section 4.4, LLD nodes 4-7 and registry/persistence contracts, approved architecture diagrams, then long-lived OpenSpec specs. The stale v3.0 filename in repository guidance is superseded for this change by that confirmation.

Affected requirements: FR-EVD-002..005, FR-POL-003/005, FR-RUL-001..005, FR-CNF-001..004, FR-WFL-001/002/004/005, FR-ARC-001..006/011/012, FR-AUD-003/004 and FR-OBS-005. Acceptance trace: Phase 007 delivery gate; UC-E2E-001 through deterministic evaluation; UC-EXC-005 (missing evidence), UC-EXC-006 (policy uncertainty), UC-EXC-007 (rule exception), UC-EXC-008 (low case confidence).

## What Changes

- Replace evidence-count checks with a versioned Evidence Completeness Service: required, available, missing, stale, invalid and conflicting evidence, per-requirement reasons, mandatory gates and completeness score.
- Formalize a Policy Eligibility Service with versioned applicability predicates before PostgreSQL lexical/vector retrieval. Reuse existing SQL filtering and ranking; persist eligibility and citation lineage.
- Introduce a governed rule registry and immutable rule-set versions, externalized parameters, eligibility/timeline/evidence/duplicate-card rules, reason codes, exception handling and execution records.
- Acquire both candidate transactions through read-only providers; a possible-duplicate reference alone cannot establish duplication.
- Compute explainable case confidence from classification, completeness, retrieval, rule certainty, conflicts and provider/tool failures using versioned configuration. Mandatory gates override any aggregate score.
- Pin facts, evaluation time, evidence contract and snapshot, policy/citations, applicability version, rule set, and confidence formula/thresholds. Retrying identical evaluations reuses results; explicit re-evaluation creates linked immutable records.
- Extend the graph through rules and confidence to a deterministic disposition candidate ready for the next recommendation stage. Persist evidence/manual/supervisor requests and gated checkpoints; expose factors and rule results in API and a focused read-only UI.

## Capabilities

### New Capabilities

- None; implement and extend existing capability contracts.

### Modified Capabilities

- `evidence-management`: Configuration-driven completeness, freshness/conflicts and durable evidence request.
- `policy-rag`: Versioned pre-retrieval eligibility decisions and immutable selected-policy lineage.
- `deterministic-rules`: Registry, deterministic duplicate-card evaluation, execution records and regression governance.
- `case-confidence-and-escalation`: Reproducible factor computation, hard gates and explainable review routing.
- `workflow-orchestration`: Phase 007 nodes, pinned evaluation bundles, durable requests, resume and downstream boundary.
- `audit-governance`: Correlated deterministic-control, configuration and re-evaluation lineage.
- `observability-evaluation`: Golden datasets, boundary/security tests and repeatability gates.

## Impact

- Backend: typed control contracts, deterministic services, repositories, additive Alembic migration, provider candidate lookup, workflow graph/service integration, read APIs and synthetic smoke/evaluation utilities.
- Database: immutable version/configuration and evaluation records; durable review/evidence requests; checkpoint references. PostgreSQL remains durable authority and nested services do not commit the outer workflow transaction.
- Frontend: focused evaluation details showing completeness, deterministic rule outcomes, confidence factors, pinned versions and review reasons separately from any AI rationale.
- Compatibility: existing case and policy endpoints remain available; existing checkpoints stay readable and are not silently upgraded to new rules. No new model provider or autonomous agent dependency.
- Out of scope: AI evidence extraction/OCR, real banking integrations, UPI/ATM investigation expansion, full recommendation generation (Phase 008), reviewer assignment/approval/rework lifecycle, customer messaging, financial posting and final case disposition. Minimal durable review requests support current fail-closed gates without claiming completion of Phase 008 HITL.
- Exit: duplicate-card evaluation reaches a deterministic disposition recommendation **path** using pinned evidence contract, policy, rules and thresholds, with complete lineage. This is a candidate for later grounded recommendation and mandatory human decision, never approval to move money.
