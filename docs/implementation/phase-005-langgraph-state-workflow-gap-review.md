# Phase 005 LangGraph State and Workflow Gap Review

Phase 005 follows FRD v3.1 `FR-WFL-001`, `FR-WFL-002`, `FR-WFL-003`, `FR-WFL-004`, `FR-WFL-005`, `FR-ARC-001`, `FR-ARC-002`, `FR-ARC-003`, `FR-ARC-004`, `FR-ARC-005`, `FR-ARC-008`, `FR-ARC-011`, `FR-ARC-012`, `FR-CTX-004`, `FR-CTX-005`, `FR-EVD-004`, `FR-POL-006`, `FR-AUD-001`, `FR-AUD-002`, `FR-AUD-003`, `FR-AUD-004`, `FR-OBS-001`, `FR-OBS-002`, `FR-OBS-005` and `FR-OBS-006`.

The implemented scope is the first explicit LangGraph orchestration slice over existing case, provider-context, evidence and policy-retrieval capabilities. Model Gateway calls, AI classification, AI evidence analysis, recommendation generation, durable HITL task assignment, customer communication and financial posting remain out of scope.

## Current Baseline

- Case creation, retrieval, evidence metadata, provider context and business audit events are durable and pre-orchestration.
- Controlled policy ingestion and hybrid policy retrieval exist before Phase 005 and already accept optional workflow identifiers.
- No workflow run table, checkpoint table, workflow API, LangGraph dependency or workflow service existed before this change.
- `docs/implementation/8-WEEK-ROADMAP.md` still has older numbering for LangGraph; FRD v3.1 clarifies delivery phases and runtime workflow stages must not be conflated.

## Implementation Notes

- Added explicit workflow start, detail and resume APIs instead of changing case creation semantics.
- Added PostgreSQL workflow run and checkpoint persistence with separate workflow-state ownership.
- Added compact workflow state contracts that keep full provider payloads, evidence binaries, secrets and tokens out of checkpoint state.
- Added a bounded LangGraph path for intake, deterministic classification routing, authoritative-context reference capture, evidence gating, policy-context resolution and controlled Phase 005 stop/interrupts.
- Added workflow audit-visible events, telemetry metadata, idempotent command replay and optimistic resume checks.
- Added architecture-boundary tests proving Phase 005 does not add direct model-provider calls, recommendation execution, customer communication or financial posting.

## Validation Evidence

- `uv sync`: succeeded after adding LangGraph.
- `uv run alembic -c alembic.ini upgrade head --sql`: generated `workflow_runs`, `workflow_checkpoints`, `uq_workflow_active_case`, checkpoint sequence, state version, state hash and side-effect-key DDL.
- `uv run alembic -c alembic.ini upgrade head`: upgraded local PostgreSQL to `20260905_0005`.
- `uv run alembic -c alembic.ini current`: reported `20260905_0005 (head)`.
- `uv run ruff check .`: passed.
- `uv run mypy app tests`: passed with no issues in 41 source files.
- `uv run pytest`: `63 passed`.
- `uv run python -m app.workflow_smoke`: passed through submitted case creation, workflow start, intake, deterministic classification, authoritative-context references, evidence gate, policy retrieval and controlled Phase 005 stop before recommendation/HITL/communication/finalization.
- Live smoke output included workflow ID, case ID, state version `3`, checkpoint sequence `2`, current node `controlled_stop`, six authoritative-context references, retrieved policy context, `CONTROLLED_STOP`, correlation ID and workflow telemetry.

- `npx.cmd -y @fission-ai/openspec@1.10.0 validate 005-langgraph-state-workflow --type change --strict`: passed before archive.
- `npx.cmd -y @fission-ai/openspec@1.10.0 archive 005-langgraph-state-workflow -y --json`: archived the change as `openspec/changes/archive/2026-09-05-005-langgraph-state-workflow` and synced 15 added requirements into long-lived specs.
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`: passed after archive with `18 passed, 0 failed`.
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`: reported `18 passed, 1 failed` because of the separate active `normalize-rfc2119-requirements` change.
