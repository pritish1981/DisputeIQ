## Context

See `proposal.md` for motivation. The current backend has durable case persistence, evidence metadata, read-only synthetic provider context, policy ingestion, policy retrieval, audit records and FastAPI route patterns. It does not have LangGraph dependencies, workflow run/checkpoint tables, workflow APIs or workflow services. Existing case creation intentionally remains pre-orchestration, so Phase 005 must add explicit start/resume commands instead of changing `POST /api/v1/cases`.

Source hierarchy review found one sequencing note to reconcile: `docs/implementation/8-WEEK-ROADMAP.md` labels LangGraph orchestration as week/change 003, while FRD v3.1 says phase numbers and the 11-stage runtime workflow must not be conflated. Because Phases 003 and 004 already delivered policy ingestion and retrieval, this change treats Phase 005 as the first approved LangGraph state/workflow increment over the current code baseline.

## Goals / Non-Goals

**Goals:**

- Add a real LangGraph-backed Workflow Service that can start, inspect and resume a duplicate-card investigation workflow.
- Persist workflow runs and checkpoints in PostgreSQL through a logical checkpoint contract separate from cases, policy tables, Redis and audit.
- Keep workflow state compact, typed, versioned and resumable with optimistic concurrency.
- Use existing deterministic/provider/policy services as bounded node dependencies where they already exist.
- Record workflow lifecycle, node, checkpoint, interrupt, retry and resume lineage in API responses, audit-visible records and telemetry metadata.
- Prove no autonomous financial posting, customer communication, recommendation generation or direct model-provider call is introduced.

**Non-Goals:**

- No durable human-task queue, reviewer assignment/SLA engine or final human decision lifecycle.
- No Model Gateway implementation, LLM classification, AI evidence extraction, recommendation generation or communication drafting.
- No material outcome approval, refund, credit, debit, chargeback, settlement-posting or external financial mutation.
- No frontend workflow dashboard unless explicitly approved as a follow-up task.

## Decisions

1. Use explicit workflow APIs instead of implicit case-start behavior.

   Rationale: Phase 002 specs require case creation to remain valid without LangGraph. The workflow will start through `/api/v1/workflows` commands, preserving idempotent case intake and making orchestration opt-in and auditable.

   Alternative considered: auto-start workflow inside `POST /api/v1/cases`. Rejected because it changes established Phase 002 behavior and couples case persistence to graph availability.

2. Add `workflow_runs` and `workflow_checkpoints` as Phase 005 persistence tables.

   Rationale: FRD/HLD/LLD require separate logical ownership for business state and graph checkpoints. A small SQLAlchemy repository keeps the current persistence style while leaving room for a LangGraph-native PostgreSQL checkpointer adapter later.

   Alternative considered: store checkpoint JSON in `cases.channel_metadata` or Redis. Rejected because it violates state authority separation and Redis durability constraints.

3. Keep checkpoint state as a compact Pydantic/TypedDict envelope.

   Rationale: The LLD says workflow state stores identifiers and compact artifacts while provider payloads, evidence binaries and policy corpus data stay in their owned stores. State will carry references, hashes, statuses, scores, citations and interrupt metadata, not full records.

   Alternative considered: persist full CaseResponse/provider payload snapshots in each checkpoint. Rejected because it expands PII and makes source-of-truth reconstruction ambiguous.

4. Implement a bounded Phase 005 graph path with controlled stops.

   Rationale: The current code already supports duplicate-card case detail and policy retrieval, but does not support Model Gateway, recommendation, human decision or communication. The graph should execute intake, classification routing, context-reference capture, evidence gate and policy resolution, then stop at the next unavailable or human-governed boundary.

   Alternative considered: stub all 11 nodes as successful. Rejected because that would imply completed recommendation/human/communication controls that are not implemented.

5. Treat node dependencies by component classification.

   - Platform: Workflow Service, workflow repository, checkpoint persistence, API routes, correlation.
   - Deterministic: eligibility/evidence gate checks, routing decisions, confidence/interruption checks.
   - Tool/adapter: existing synthetic provider context already persisted by Case Service, policy retrieval service as read-only controlled retrieval.
   - AI-assisted: no direct model call in Phase 005; future AI nodes must go through Model Gateway.
   - Human: Phase 005 emits controlled interrupt/resume signals only; durable task lifecycle is out of scope.

6. Enforce workflow side-effect safety with node completion records.

   Rationale: Safe resume requires knowing whether a node already completed a provider/retrieval/audit side effect. Checkpoint metadata will record node status, completed side-effect keys, and checkpoint sequence so replay resumes at the next safe boundary.

   Alternative considered: always rerun graph from the beginning. Rejected because provider/retrieval/audit effects could duplicate and because FR-WFL-005 requires resume safety.

7. Keep audit lineage in the existing business audit style, with workflow-specific metadata.

   Rationale: The project already has append-only audit models and response contracts. Phase 005 can record workflow events with workflow ID, graph version, node name, checkpoint sequence, state version and correlation ID while keeping immutable audit reconstruction consistent.

   Alternative considered: create an entirely separate immutable workflow audit table in the first slice. Deferred because the existing audit event contract can carry workflow metadata; a dedicated immutable store can be introduced later if required by audit export design.

## Risks / Trade-offs

- [Risk] LangGraph package or checkpoint adapter API may differ from assumptions. -> Mitigation: isolate graph construction behind `app.services.workflow_graph` and keep persistence through local repositories first.
- [Risk] Existing policy retrieval API requires a promoted corpus for the happy path. -> Mitigation: tests cover both promoted-corpus progression and policy-review interrupt; smoke can seed corpus using existing fixture loader.
- [Risk] Workflow state could drift from case state. -> Mitigation: persist case ID/state references, use explicit start/resume commands, and avoid mutating case status except where specs explicitly require it.
- [Risk] All-strict OpenSpec validation may still fail on the unrelated active normalization change. -> Mitigation: validate the Phase 005 change and long-lived specs separately and report unrelated active-change failures distinctly.
- [Risk] Durable HITL is not implemented in this slice. -> Mitigation: Phase 005 emits typed interrupt/resume requirements only; durable human task implementation remains a later approved change.

## Migration Plan

1. Add LangGraph dependency to `backend/pyproject.toml` and update `uv.lock`.
2. Add Alembic revision `20260905_0005_langgraph_state_workflow.py` for workflow run/checkpoint tables and indexes.
3. Add domain schemas for workflow start, detail, checkpoint, interrupt, resume and errors.
4. Add workflow repository and service with idempotent start/resume, state-version checks and audit-visible event creation.
5. Add graph state and node functions, using existing case/policy services where available and deterministic interrupts where later capabilities are absent.
6. Add `/api/v1/workflows` routes and include them in FastAPI.
7. Add unit, integration and smoke tests, then run backend, smoke and OpenSpec validation.

Rollback: remove or disable the workflow API route and do not start workflow workers. The migration is additive; existing case and policy behavior remains intact.
