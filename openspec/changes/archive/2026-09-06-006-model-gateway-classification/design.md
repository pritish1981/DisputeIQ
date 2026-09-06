## Context

See `proposal.md` for motivation. The current backend has durable case persistence, policy ingestion/retrieval, a bounded Phase 005 LangGraph workflow, compact workflow checkpoints, idempotent workflow commands, and audit-visible workflow lineage. The current classification node is deterministic Phase 005 routing for duplicate-card cases only; it does not execute an approved AI-assisted capability.

FRD v3.1 defines classification as Stage 2 of the 11-stage workflow and requires classification to cover the three MVP dispute types with structured category, confidence and supporting attributes. The FRD and LLD also require all model calls to pass through a central Model Gateway with provider abstraction, prompt/version management, token controls, response validation, guardrails, fallback/routing, kill switch and telemetry. The tech stack names provider-neutral OpenAI/Azure OpenAI/Anthropic-style support, but local validation must remain synthetic and runnable without real provider credentials.

Design reconciliation: `docs/implementation/8-WEEK-ROADMAP.md` still uses older numbering that labels broad AI capabilities as change 004 and security/audit/communication as change 006. The higher-priority FRD v3.1 and completed Phase 003-005 history establish Phase 006 as Model Gateway and Classification. This change follows FRD v3.1 and does not implement recommendation, communication, durable HITL task lifecycle, or financial finalization.

## Goals / Non-Goals

**Goals:**

- Introduce a concrete Model Gateway boundary for approved AI-assisted capabilities.
- Add provider-neutral request/response contracts, model route configuration, prompt version references, token/timeout/retry/fallback controls, response schema validation, kill-switch behavior, audit lineage and telemetry.
- Add AI-assisted classification for duplicate card transaction, failed UPI transfer, and ATM debit without cash.
- Integrate workflow classification through the classification service and Model Gateway while preserving Phase 005 start/detail/resume compatibility.
- Keep local tests and smoke deterministic with a fake provider adapter behind the gateway.
- Prove direct provider SDK calls from business/workflow/classification code are prohibited.

**Non-Goals:**

- No recommendation generation, evidence-analysis summarization, customer communication, final decisioning, durable human-task assignment, or financial posting.
- No autonomous update to authoritative provider facts, deterministic policy applicability, evidence completeness, rules, case confidence or human decisions.
- No requirement for live OpenAI/Azure/Anthropic credentials in local validation.
- No frontend workflow dashboard unless approved separately.

## Decisions

1. Add a platform-owned Model Gateway service and keep provider adapters behind it.

   Rationale: `FR-AIP-001` and `FR-AIP-002` require central routing and provider-neutral substitution. Business services should depend on gateway contracts, not provider SDKs.

   Alternative considered: call provider SDKs directly from the classification service. Rejected because it violates the source-of-truth gateway invariant and makes direct-provider-call prohibition untestable.

2. Use a deterministic local provider adapter for Phase 006 validation.

   Rationale: The project uses synthetic banking data and needs repeatable local smoke/tests without secrets. A fake provider can still exercise routing, prompt/version selection, token controls, retries/fallback, schema validation and telemetry.

   Alternative considered: require a live OpenAI or Azure OpenAI API key for Phase 006. Deferred because it would make the first gateway slice harder to validate and would mix credential onboarding with the architecture boundary.

3. Persist model invocation lineage only where it is needed for audit/evaluation.

   Rationale: Classification audit reconstruction needs model route, prompt version, schema version, token usage, attempts, fallback, validation status, confidence and correlation metadata. The raw provider payload, hidden reasoning, provider secrets and full evidence/provider payloads must not become authoritative business state or workflow checkpoint state.

   Alternative considered: store complete request/response payloads in workflow checkpoints. Rejected because it expands sensitive data and blurs source-of-truth ownership.

4. Treat classification as an AI-assisted capability with deterministic gates.

   Rationale: Model output proposes category, confidence and attributes; configured thresholds, schema validation, supported-category checks, kill switch and manual-routing decisions remain deterministic. This preserves the "deterministic before probabilistic" and "fail closed" LLD principles.

   Alternative considered: allow the model to decide whether to continue. Rejected because confidence and routing gates must be governed configuration, not prompt text.

5. Integrate Phase 006 through the existing workflow classification node without changing workflow command APIs.

   Rationale: Phase 005 already has explicit `/api/v1/workflows` start/detail/resume contracts, idempotency and checkpoint persistence. Updating the classification node and response metadata is additive and keeps existing case creation pre-orchestration.

   Alternative considered: add a separate classification API first. Deferred because the FRD frames classification as workflow Stage 2; a diagnostic endpoint can be added later if operations needs it.

6. Emit manual-classification signals, not durable HITL tasks, in this slice.

   Rationale: The classification specs require a manual-classification path, but durable HITL task lifecycle is a later capability. Phase 006 can checkpoint an interrupt/signal with reason, threshold, confidence, schema/config lineage and resume requirements without creating the full task system.

   Alternative considered: implement a human-task service now. Rejected as scope creep beyond Model Gateway and Classification.

7. Keep Phase 006 component ownership explicit.

   - AI-assisted: Classification Service.
   - Platform: Model Gateway, model route registry, prompt/config registry, schema validation, token/timeout/retry/fallback policy, telemetry.
   - Deterministic: classification threshold gate, supported-category gate, kill-switch bypass, data policy checks, workflow routing decisions.
   - Tool/adapter: gateway provider adapters and existing read-only synthetic banking providers.
   - Human: manual-classification signal only; durable reviewer task lifecycle remains out of scope.

## Risks / Trade-offs

- [Risk] A fake provider may hide real provider integration issues. -> Mitigation: design provider-neutral adapters and add contract tests for request/response normalization, timeouts, fallback and schema-validation failure paths.
- [Risk] Classification for UPI and ATM categories could advance into unsupported downstream workflow behavior. -> Mitigation: allow classification but route unsupported downstream prerequisites to controlled workflow boundaries until later phases implement those paths.
- [Risk] Gateway telemetry/audit metadata could include sensitive prompt or provider payload content. -> Mitigation: store configuration versions, hashes, token counts and status metadata; do not persist raw provider payloads, hidden reasoning, secrets or full evidence/provider data in checkpoints.
- [Risk] The kill switch could be implemented as a static test flag rather than an operator-controlled configuration. -> Mitigation: centralize it in gateway/classification configuration and expose it through service configuration used by workflow tests and smoke.
- [Risk] `validate --all --strict` may continue to fail because of unrelated active normalization deltas. -> Mitigation: validate the Phase 006 change and long-lived specs separately, and report unrelated active-change failures distinctly.

## Migration Plan

1. Add additive schema/configuration and tests first: classification output schemas, gateway request/response schemas, config objects, fake provider and validation helpers.
2. Add Model Gateway service and provider abstraction with deterministic local provider, token/data-policy checks, timeout/retry/fallback metadata and kill-switch behavior.
3. Add Classification Service using the gateway and deterministic routing gates for supported category, confidence threshold, malformed output and unsupported category.
4. Integrate the Phase 005 workflow classification node with the Classification Service and update checkpoint/audit/telemetry metadata without changing workflow start/detail/resume request contracts.
5. Add smoke/evaluation commands and README guidance for local validation.

Rollback: disable AI-assisted classification through the kill switch or route configuration. Existing case creation, policy retrieval and workflow APIs remain available, and the classification node can route to manual-classification interrupts without provider execution.
