# Phase 007 implementation review

Reviewed 2026-09-10 against the approved proposal, design, seven delta specs and
`DisputeIQ_FRD_v3.1.docx` requirement traceability. The user explicitly selected FRD v3.1
and approved implementation. The older v3.0 repository reference does not override that selection.

## Disposition

All 32 implementation/validation tasks are complete for the approved synthetic pilot scope.
The user accepted Phase 007 on 2026-09-10. All seven delta specs were synchronized and the change was archived on that date. It has not been committed or pushed.
The repository-wide strict validation gate remains red for the unrelated normalization change.

## Scope and evidence

| Tasks | Implementation | Verification |
| --- | --- | --- |
| 1.1–1.5 | Typed contracts, canonical hashes, immutable configuration registry and storage | Invalid config/hash tests, failed regression rejection, live additive migration, uniqueness and scoped foreign keys |
| 2.1–2.4 | Read-only paired context, provenance, checklist scoring, missing/stale/invalid/conflicting evidence and requests | Unit boundaries/optional/duplicate evidence, provider failure/lineage tests, live evidence reassessment and fulfillment |
| 3.1–3.3 | Shared deterministic admission service, restricted PostgreSQL FTS/pgvector query, exact policy pins | Nine live SQL predicate/boundary checks; revocation/content/effective/channel tests; retained/new corpus tests |
| 4.1–4.4 | Six registry handlers, deterministic dispositions, reason codes and durable execution/error records | Independent golden cases, recomputation with reordered facts, same-ID/nonmatch/refund/timeline cases, exception/manual request tests |
| 5.1–5.3 | Decimal weighted confidence, explicit factor provenance, mandatory gates, versioned thresholds | Golden arithmetic/equality/unknown inputs, supervisor request test, effective threshold-version transition preserving history |
| 6.1–6.4 | Explicit controls graph, atomic results/requests/audit/checkpoints, typed re-evaluation, old graph compatibility | Transaction rollback tests, live concurrent/stale resume, separate-process idempotent replay, old graph smoke, UPI/ATM resume guards |
| 6.5–6.7 | Workflow-scoped read APIs, React viewer, correlated control/request/re-evaluation audit and telemetry | Access/404/422/forgery tests, no raw provider payloads, six frontend tests, live browser inspection and audit-count replay assertions |
| 7.1–7.6 | Versioned golden suite, PostgreSQL smoke, regression checks and README runbook | Results below; commands and limitations documented in README |

## Observed results

- `uv run ruff check .`: passed.
- `uv run mypy app tests`: passed, 63 source files.
- `uv run pytest`: 114 passed.
- `uv run python -m app.control_regression`: 23 scenarios passed.
- Live PostgreSQL upgraded from `20260905_0005` through `20260908_0007` to
  `20260910_0007b`; existing graph code/readers remain compatible.
- `uv run python -m app.control_smoke`: passed. Example final run:
  - workflow `e121bbcf-3aab-498e-b4da-06559670f534`
  - evaluation `4c57acda-8ce1-4ba0-9eac-0e066ce227b1`
  - candidate `DUPLICATE_SUPPORTED`, score `0.855404`, threshold `0.70`
  - graph `duplicate-card-controls-v1`, exit `CONTROLLED_STOP / deterministic_disposition_ready`
  - evidence `duplicate-card-evidence-v1`, applicability `policy-eligibility-v1`,
    rules `duplicate-card-rules-v1`, confidence `case-confidence-v1`
  - corpus `controls-corpus-2617eda78d`; exact citations/index/retrieval configuration
    and upstream result hashes retained in the immutable policy/confidence records
  - concurrent resumes: one accepted, one stale; restart/idempotent replay, evidence
    fulfillment, append-only enforcement, scoped foreign keys and uniqueness all passed
- Live SQL exclusions passed for product, channel, jurisdiction, inactive status,
  unapproved document, ineffective policy, unmapped family and unavailable index;
  inclusive effective-date admission also passed. Mutations used for those checks were rolled back.
- `uv run python -m app.classification_eval`: passed.
- Legacy `app.policy_retrieval_smoke`: retrieved at `0.541734`, evaluation passed.
- Legacy `app.workflow_smoke`: retained `duplicate-card-workflow-v1` controlled stop.
- Frontend lint/typecheck/build passed; vitest: 6 passed.
- Browser at localhost:5173 showed the original blocked evidence assessment, fulfilled
  request, linked successful assessment, policy citations, six rule findings and all six
  confidence contributions. Tables support horizontal scrolling in narrow panels.
- `openspec validate 007-deterministic-rules-confidence --strict`: passed.
- `openspec validate --all --strict`: 19 passed, 1 failed. The failure is
  `normalize-rfc2119-requirements`; its stale MODIFIED deltas are separate from Phase 007.

## Implementation notes and limits

- The immutable evaluation root pins inputs/time/profile; immutable child stages pin the
  admitted policy and result lineage. The confidence record contains the complete exit pin
  manifest, including policy citations and exact confidence configuration. This avoids
  mutating the root when later stages finish.
- A second additive migration adds composite case/workflow/prior-evaluation foreign-key
  scoping after the base controls schema. No destructive migration was used.
- Access uses the existing pilot header convention: `X-Control-Reader: true` on local/test
  control APIs. Production access fails closed. This is not production authentication or RBAC.
- Synthetic evidence validation is restricted to known fixture metadata in local/test;
  file extraction/OCR and real evidence-validation integrations remain out of scope.
- The reviewed weights, evidence contract, filing/window limits and threshold are pilot
  parameters. Production thresholds require approved calibration and regression evidence.
- Standalone legacy retrieval keeps metadata-based compatibility; the Phase 007 graph
  always supplies its explicit versioned policy-family/document mapping before scoring.
- Review records are minimal durable gate requests. Full reviewer assignment, adjudication,
  grounded recommendations, communications and financial actions belong to later phases.
- Docker was temporarily unavailable during a final rerun. After restarting the local
  services, the complete live smoke passed again. PostgreSQL reported an existing collation
  version warning; no collation maintenance or database rebuild was performed in this phase.

No approved Phase 007 application capability remains unimplemented. User acceptance and archive/spec synchronization are complete. Git publication remains outstanding.

## Post-acceptance archive verification

All seven capability deltas are present in the main specs with existing content preserved.
`validate --specs --strict`: 18 passed, 0 failed. The archive is
`openspec/changes/archive/2026-09-10-007-deterministic-rules-confidence`.
Post-archive `validate --all --strict`: 18 passed, 1 unrelated normalization change failed.
