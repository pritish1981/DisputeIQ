## 1. Baseline Review and Boundary Tests

- [x] 1.1 Review existing Phase 005 workflow graph, workflow service, schema, audit, telemetry and architecture-boundary tests against `FR-CLS-001` through `FR-CLS-004` and `FR-AIP-001` through `FR-AIP-006`; verify findings are captured in `docs/implementation/phase-006-model-gateway-classification-gap-review.md`.
- [x] 1.2 Add or update architecture-boundary tests proving business, workflow, classification, policy, recommendation and communication code cannot call model-provider SDKs directly and verify `uv run pytest tests/integration/test_architecture_boundaries.py` fails before implementation and passes after implementation.
- [x] 1.3 Confirm Phase 006 scope excludes recommendation, communication, durable HITL task lifecycle, decision rules, final case decisions and financial posting; verify the gap review and boundary tests name the excluded runtime paths.

## 2. Model Gateway Contracts and Configuration

- [x] 2.1 Add provider-neutral Model Gateway request, response, provider result, route configuration, prompt reference, token budget, fallback, validation and telemetry schemas; verify `uv run pytest tests/unit/test_schemas.py` covers valid and invalid payloads.
- [x] 2.2 Add versioned classification output schema containing supported category, confidence, supporting extracted attributes, schema version, prompt version, model route version and correlation ID; verify schema tests reject malformed output and unsupported state mutation fields.
- [x] 2.3 Add configurable AI kill switch, classification confidence threshold, token budget, timeout, retry and fallback policy settings with deterministic defaults for local validation; verify unit tests cover enabled, disabled and missing-config behavior.
- [x] 2.4 Add data-policy and prompt-injection guard helpers that treat case text, evidence excerpts, provider facts and policy text as untrusted model input; verify tests prove prompt-like input cannot change system instructions, routing policy, tool permissions or financial authority.

## 3. Model Gateway Service and Provider Adapters

- [x] 3.1 Implement the Model Gateway service with provider-neutral execution, route resolution, prompt/config version metadata, token checks, timeout/retry/fallback metadata and schema validation; verify `uv run pytest tests/unit/test_model_gateway.py` covers success, retry, fallback, timeout, token and validation paths.
- [x] 3.2 Implement a deterministic local classification provider adapter behind the Model Gateway for duplicate-card, failed-UPI, ATM debit-without-cash, unsupported and malformed-output fixtures; verify provider contract tests pass without real provider credentials.
- [x] 3.3 Ensure the Model Gateway returns only validated structured fields and redacted metadata to business capabilities; verify tests prove raw provider payloads, hidden reasoning, secrets and full evidence/provider payloads are not persisted into workflow state.
- [x] 3.4 Add audit-visible Model Gateway invocation metadata for accepted, retried, fallback, bypassed and failed requests; verify tests prove audit failure blocks accepted automated continuation.

## 4. Classification Service and Routing Gates

- [x] 4.1 Implement the Classification Service using the Model Gateway and verify supported duplicate-card, failed-UPI and ATM debit-without-cash categories return structured output above configured threshold.
- [x] 4.2 Implement deterministic classification routing gates for low confidence, unsupported category, malformed output, provider failure, missing configuration and kill-switch bypass; verify unit tests route each case to manual-classification signal without inventing a supported category.
- [x] 4.3 Record classification correction/evaluation lineage fields for original category, corrected category, confidence, reviewer rationale placeholder, schema version, prompt version and model route version; verify tests cover evaluation metadata generation without authorizing financial outcomes.
- [x] 4.4 Add classification telemetry metadata for case ID, workflow ID, correlation ID, provider route reference, prompt version, schema version, latency, token usage, attempts, fallback, kill-switch state and confidence outcome; verify unit tests cover correlated success and failure telemetry.

## 5. Workflow Integration

- [x] 5.1 Update the LangGraph classification node to invoke the Classification Service through the Model Gateway and verify `uv run pytest tests/unit/test_workflow_graph.py` covers the happy path and manual-classification interrupts.
- [x] 5.2 Update workflow checkpoint serialization to include compact classification category, confidence, extracted attributes, prompt/schema/route versions, side-effect key and telemetry references; verify state-contract tests reject raw provider payloads, hidden reasoning, secrets and oversized model content.
- [x] 5.3 Preserve workflow start/detail/resume API compatibility while returning Phase 006 classification stage summaries, interrupt metadata and telemetry; verify `uv run pytest tests/integration/test_workflow_api.py` covers start, replay, inspect, stale resume and kill-switch/manual-classification cases.
- [x] 5.4 Ensure idempotent workflow retry/resume does not duplicate accepted classification model invocations, checkpoints or audit events; verify safe-resume tests assert one classification side-effect key for an accepted classification result.

## 6. Evaluation, Smoke, Documentation and OpenSpec Validation

- [x] 6.1 Add `uv run python -m app.classification_eval` or equivalent deterministic evaluation command covering supported categories, unsupported routing, low-confidence routing, schema validity, kill switch and fallback; verify the command prints threshold outcomes and fails mandatory failures.
- [x] 6.2 Add or update a Phase 006 smoke command that creates or loads a submitted case, starts workflow classification through the Model Gateway, checkpoints the result or manual interrupt, and prints workflow ID, case ID, category, confidence, schema/prompt/route versions, state version, correlation ID and telemetry; verify the smoke passes against local PostgreSQL without real provider credentials.
- [x] 6.3 Update README and backend runbook with Phase 006 startup, configuration, backend, Swagger, smoke and evaluation validation steps; verify documented commands match implemented endpoints and expected outputs.
- [x] 6.4 Run backend quality gates `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest`, and record the results in the Phase 006 gap review.
- [x] 6.5 Run `npx.cmd -y @fission-ai/openspec@1.10.0 validate 006-model-gateway-classification --type change --strict` and `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`, and report any unrelated active-change failures separately from Phase 006.
- [x] 6.6 Confirm `git diff --check` and `git status --short --branch`, and report changed files, tests run, remaining risks and implementation deviations before archive approval.
