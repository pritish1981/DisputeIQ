## 1. Baseline Review and Dependency Setup

- [x] 1.1 Review current backend case, policy retrieval, audit, repository, migration and architecture-boundary tests against Phase 005 specs and verify findings are captured in `docs/implementation/phase-005-langgraph-state-workflow-gap-review.md`.
- [x] 1.2 Add LangGraph dependency to `backend/pyproject.toml`, refresh `backend/uv.lock`, and verify `uv sync` succeeds from `backend/`.
- [x] 1.3 Add architecture-boundary tests proving Phase 005 exposes no direct model-provider calls, recommendation execution, customer communication, or financial posting tools, and verify `uv run pytest tests/integration/test_architecture_boundaries.py` fails before implementation and passes after implementation.

## 2. Workflow Persistence and State Contracts

- [x] 2.1 Add Alembic migration for `workflow_runs` and `workflow_checkpoints` with separate workflow-state ownership, active-run uniqueness for normal mode, checkpoint sequence/state-version indexes, and verify `uv run alembic -c alembic.ini upgrade head --sql` includes the expected DDL.
- [x] 2.2 Add SQLAlchemy workflow run/checkpoint models and repository methods for create, detail, latest checkpoint, append checkpoint, compare-and-swap state version, and idempotent command replay, and verify repository unit tests cover success and conflict paths.
- [x] 2.3 Add Pydantic workflow schemas for start, detail, checkpoint summary, interrupt metadata, stage summaries, resume command, telemetry and structured errors, and verify `uv run pytest tests/unit/test_schemas.py` covers valid and invalid payloads.
- [x] 2.4 Implement compact workflow state serialization that stores identifiers, references, stage outputs, side-effect keys and control/error metadata without full provider payloads, evidence binaries, secrets or tokens, and verify state-contract tests reject oversized or disallowed fields.

## 3. LangGraph Runtime and Node Boundaries

- [x] 3.1 Implement the Phase 005 graph builder and typed state envelope for intake, classification routing, authoritative-context reference capture, evidence gate, policy-context resolution and controlled stop nodes, and verify graph unit tests cover happy-path ordering.
- [x] 3.2 Implement node allow-list enforcement for service/tool operations and fail-closed violations with workflow ID, node name and correlation ID metadata, and verify authorization tests cover denied operations.
- [x] 3.3 Implement deterministic intake/classification routing for the duplicate-card slice without direct LLM calls, and verify low-confidence or unsupported categories interrupt to manual-classification status.
- [x] 3.4 Implement authoritative-context reference capture using existing persisted provider context rather than re-fetching or replacing provider facts, and verify resume tests do not duplicate provider side effects.
- [x] 3.5 Implement deterministic evidence completeness gating for Phase 005, including missing-evidence interrupt state and resume requirements, and verify tests cover available and missing evidence cases.
- [x] 3.6 Implement policy-context resolution using existing hybrid retrieval with workflow ID propagation, including policy-review interrupt on abstention or low confidence, and verify tests cover retrieved and abstained policy outcomes.
- [x] 3.7 Implement controlled stop behavior before recommendation, durable human decision, communication and financial finalization, and verify graph tests prove no material outcome is finalized in Phase 005.

## 4. Workflow Service and API

- [x] 4.1 Implement `WorkflowService.start_workflow` with idempotency, active-run conflict handling, initial checkpoint, workflow-start audit lineage and correlation propagation, and verify service tests cover create, replay and conflict.
- [x] 4.2 Implement workflow detail/query behavior returning status, current node, state version, checkpoint sequence, interrupt metadata, stage summaries, error metadata and correlation ID, and verify service/API tests cover existing and missing workflow IDs.
- [x] 4.3 Implement `WorkflowService.resume_workflow` with `If-Match` state-version validation, idempotency, latest-checkpoint load and safe continuation, and verify stale resume returns conflict without state mutation.
- [x] 4.4 Add `/api/v1/workflows` routes for start, detail and resume with versioned schemas, structured errors and `X-Correlation-ID`, and verify `uv run pytest tests/integration/test_workflow_api.py` covers success, replay, not-found and conflict responses.
- [x] 4.5 Wire workflow routes into FastAPI without changing `POST /api/v1/cases` pre-orchestration behavior, and verify existing case API tests still pass.

## 5. Audit, Telemetry and Resume Safety

- [x] 5.1 Add workflow lifecycle, node completed, checkpoint, interrupt, resume and failure audit-visible events with case ID, workflow ID, graph version, node name, checkpoint sequence, state version and correlation ID, and verify audit tests reconstruct workflow progression.
- [x] 5.2 Add telemetry metadata for node latency, attempts, retries, checkpoint count, interrupts and outcomes, and verify unit/API responses expose correlated workflow telemetry.
- [x] 5.3 Add side-effect-key tracking so retries/resumes skip completed provider, retrieval and audit side effects, and verify safe-resume tests prove completed effects are not duplicated.
- [x] 5.4 Add workflow error classification for retriable, manual-degradation, validation and fatal failures, and verify tests cover retry exhaustion and controlled manual-processing status.

## 6. Smoke, Documentation and OpenSpec Validation

- [x] 6.1 Add `uv run python -m app.workflow_smoke` to create or load a duplicate-card case, start workflow, checkpoint through available stages, exercise a controlled stop/interrupt and print workflow ID, state version, checkpoint sequence, current node, correlation ID and audit lineage; verify the smoke passes against local PostgreSQL.
- [x] 6.2 Update README and backend runbook with Phase 005 startup, migration, backend, Swagger and smoke validation steps, and verify the documented commands match implemented endpoints.
- [x] 6.3 Run backend quality gates `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest`, and record the results in the Phase 005 gap review.
- [x] 6.4 Run `npx.cmd -y @fission-ai/openspec@1.10.0 validate 005-langgraph-state-workflow --type change --strict` and `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`, and report any unrelated active-change failures separately from Phase 005.
- [x] 6.5 Confirm `git diff --check` and `git status --short --branch`, and report changed files, tests run, remaining risks and implementation deviations before archive approval.
