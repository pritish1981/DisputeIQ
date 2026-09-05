## Why

DisputeIQ now has durable case persistence, authoritative synthetic context, controlled policy ingestion, and hybrid policy retrieval, but no approved runtime workflow boundary that starts, checkpoints, resumes, and audits an investigation. Phase 005 introduces the first LangGraph-backed state and workflow slice so submitted duplicate-card cases can move from pre-orchestration case intake into governed orchestration without giving LangGraph authority over facts, policy, rules, human decisions, communications, or financial posting.

## What Changes

- Add a Workflow Service and protected workflow APIs to start, inspect, and resume a workflow for an existing submitted case.
- Add durable PostgreSQL workflow-run and checkpoint persistence logically separated from case business state, policy knowledge, Redis, and immutable audit records.
- Add a typed LangGraph state envelope carrying compact identifiers, stage outputs, interrupt metadata, retry/error metadata, state version, case ID, workflow ID, and correlation ID.
- Add a first duplicate-card investigation graph that executes bounded orchestration stages for intake, classification routing, authoritative-context reference capture, evidence completeness gating, and policy-context resolution using existing deterministic/provider/retrieval services where available.
- Add controlled interrupt outcomes for missing evidence, policy-review needs, unsupported or low-confidence classification, and later-phase recommendation/human-decision boundaries.
- Add workflow lifecycle and node audit/telemetry events with case ID, workflow ID, correlation ID, graph version, node name, checkpoint sequence, status, and state version.
- Add safe idempotent start/resume behavior that does not duplicate completed side effects or existing material audit events.
- Keep Phase 002 Case API creation pre-orchestration unless the workflow start endpoint is explicitly invoked.
- Do not add autonomous financial posting, customer communication, durable human-task lifecycle, recommendation generation, direct model-provider calls, or LLM-owned authoritative facts.

## Capabilities

### New Capabilities

- `workflow-orchestration`: Defines the LangGraph workflow runtime contract, typed state envelope, start/resume/query behavior, node routing, interrupts, and safe duplicate-card workflow progression.

### Modified Capabilities

- `workflow-resilience`: Adds concrete persisted workflow run/checkpoint behavior, compare-and-swap resume/version semantics, retry classification, and manual-degradation boundaries for Phase 005.
- `architecture-flow-controls`: Adds the Phase 005 orchestration boundary where LangGraph coordinates routing and checkpoints while designated deterministic/provider/policy services retain authority.
- `api-integrations`: Adds versioned workflow API contracts and structured workflow error responses.
- `audit-governance`: Adds workflow lifecycle and node audit lineage needed to reconstruct starts, checkpoints, interrupts, resumes, and failures.
- `observability-evaluation`: Adds workflow telemetry correlation for node execution, checkpoint count, interrupts, retries, latency, and workflow outcome.

## Impact

- Backend dependencies: add LangGraph plus any required checkpoint adapter dependency approved by the implementation design.
- Backend database: add Alembic migration for workflow run/checkpoint persistence and indexes; keep checkpoint storage logically separate from operational case state.
- Backend API: add `/api/v1/workflows` endpoints for start, detail, and resume/query operations with idempotency, optimistic concurrency, and correlation headers.
- Backend domain/services: add typed workflow state contracts, workflow repository, workflow service, graph builder/nodes, tool allow-list enforcement hooks, retry/error taxonomy, audit events, and smoke command.
- Tests: add unit and integration coverage for state schema, graph routing, checkpoint persistence, idempotent start/resume, no duplicated side effects, interrupts, audit lineage, API contracts, and architecture boundaries.
- Documentation: update local runbook and validation steps after implementation.
