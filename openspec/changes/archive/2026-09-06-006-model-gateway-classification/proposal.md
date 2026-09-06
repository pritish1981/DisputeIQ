## Why

Phase 005 introduced bounded LangGraph orchestration but intentionally kept classification deterministic and stopped before approved AI execution. Phase 006 is needed to add the FRD-governed Model Gateway and the first AI-assisted classification capability so submitted disputes can be classified through a controlled, provider-neutral, schema-validated path without giving AI authority over banking facts, rules, recommendations, communications, or material financial outcomes.

Affected FRD requirements: `FR-CLS-001`, `FR-CLS-002`, `FR-CLS-003`, `FR-CLS-004`, `FR-AIP-001`, `FR-AIP-002`, `FR-AIP-003`, `FR-AIP-004`, `FR-AIP-005`, `FR-AIP-006`, `FR-AUD-003`, `FR-AUD-004`, `FR-OBS-001`, `FR-OBS-002`, `FR-OBS-005`, `FR-OBS-006`, `FR-ARC-001`, `FR-ARC-006`, `FR-ARC-007`, `FR-ARC-011`, and `FR-ARC-012`.

## What Changes

- Add a central Model Gateway for approved AI-assisted capabilities, including provider-neutral request/response contracts, model routing policy, prompt/template version references, timeout/retry/fallback behavior, token budget enforcement, data policy checks, structured response validation, and correlated telemetry.
- Add an operator-controlled AI kill switch that bypasses model execution and routes classification to safe manual handling for new or in-flight workflow cases.
- Replace the Phase 005 deterministic classification node with a Phase 006 classification service that invokes the Model Gateway and returns versioned structured classification output for the three MVP dispute types: duplicate card transaction, failed UPI transfer, and ATM debit without cash.
- Add confidence and unsupported-category gates so low-confidence, malformed, unavailable, or unsupported classification outcomes pause automated progression with a manual-classification signal.
- Record model, prompt, schema, routing, token, latency, confidence, fallback, and validation lineage in workflow checkpoint state, audit-visible events, and telemetry metadata.
- Preserve deterministic authority boundaries: provider facts, policy eligibility, evidence completeness, rules, case confidence, human decisions, customer communication, and financial posting remain outside LLM authority.
- No breaking changes to existing case creation, policy ingestion, policy retrieval, workflow start/detail/resume, or Phase 005 checkpoint contracts.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ai-platform-model-gateway`: Define concrete Phase 006 Model Gateway execution, provider abstraction, prompt/config governance, token controls, response validation, telemetry, fallback, and kill-switch behavior.
- `classification-and-routing`: Expand classification from long-lived intent into an executable AI-assisted duplicate-card/UPI/ATM classification contract with structured schema, thresholds, unsupported-category handling, manual-classification routing, and evaluation lineage.
- `workflow-orchestration`: Update the classification node boundary so LangGraph routes through the classification service and Model Gateway while preserving durable checkpoint, interrupt, resume, and side-effect safety.
- `architecture-flow-controls`: Add Phase 006 architecture boundaries proving all model calls go through the Model Gateway and AI classification cannot own authoritative facts, policy/rule outcomes, communication, or material financial outcomes.
- `audit-governance`: Add audit lineage requirements for model gateway invocations, classification outcomes, prompt/schema/config versions, validation failures, fallback, and manual-classification routing.
- `observability-evaluation`: Add correlated AI/classification telemetry and deterministic evaluation checks for schema validity, confidence gates, unsupported categories, kill switch, fallback, and direct-provider-call prohibition.
- `security-privacy`: Add Phase 006 data policy and prompt-injection boundaries for model inputs, provider responses, evidence excerpts, and classification prompts.

## Impact

- Backend: Model Gateway contracts/services/adapters/configuration, classification service, LangGraph classification node integration, workflow checkpoint metadata, audit event metadata, API response fields where needed, smoke/evaluation scripts, and tests.
- Database: additive persistence only if needed for model invocation/audit/evaluation lineage; no destructive migration and no changes to existing case or workflow primary keys.
- APIs: existing workflow start/detail/resume behavior remains compatible; any new diagnostic/admin endpoints must be read-oriented or explicitly protected.
- Dependencies: may add provider SDK abstractions or test doubles, but business services must not import provider SDKs directly.
- Runtime: synthetic/local classification should be testable without real provider credentials; real provider invocation remains behind the Model Gateway and kill switch/config controls.
- Out of scope: recommendation generation, evidence analysis beyond classification inputs, durable HITL task lifecycle, customer communication, final case decisioning, refunds, credits, debits, chargebacks, settlement posting, and autonomous money movement.
