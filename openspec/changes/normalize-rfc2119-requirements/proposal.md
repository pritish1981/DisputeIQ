# Normalize OpenSpec Requirement Language

## Why

Project-wide strict OpenSpec validation is blocked because 35 existing requirements across 17 long-lived capabilities do not contain an explicit RFC 2119 normative keyword. Their scenarios already describe the required behavior, but the requirement statements must use `SHALL` or `MUST` so the specifications are unambiguously normative and pass strict validation.

## What Changes

- Add a concise `SHALL` or `MUST` statement to each of the 35 affected requirements.
- Preserve every existing requirement title, FRD reference, GWT scenario, capability boundary and architectural invariant.
- Make no application, API, database, workflow, test or runtime behavior changes.
- Verify the normalization with change-level and project-wide strict OpenSpec validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-platform-model-gateway`: Normalize model gateway, structured-response validation and kill-switch requirements.
- `api-integrations`: Normalize versioned REST contract and correlation identifier requirements.
- `architecture-flow-controls`: Normalize orchestrator and state-authority separation requirements.
- `audit-governance`: Normalize material-event and decision-reconstruction requirements.
- `authoritative-context`: Normalize authoritative banking fact and tool authorization requirements.
- `case-confidence-and-escalation`: Normalize governed-confidence and low-confidence escalation requirements.
- `case-intake-and-management`: Normalize the idempotent mutation requirement; its other requirements are already normative.
- `classification-and-routing`: Normalize classification and low-confidence routing requirements.
- `communication-and-closure`: Normalize approved-outcome and deterministic closure requirements.
- `deterministic-rules`: Normalize core rules-engine and versioned-result requirements.
- `evidence-management`: Normalize evidence-completeness and missing-evidence interrupt requirements.
- `human-in-the-loop`: Normalize mandatory material review and reviewer-action requirements.
- `observability-evaluation`: Normalize technical-correlation and AI release-gate requirements.
- `policy-rag`: Normalize deterministic applicability, cited retrieval and low-confidence requirements.
- `recommendation`: Normalize grounded recommendation and no-autonomous-execution requirements.
- `security-privacy`: Normalize protected-access and untrusted-content boundary requirements.
- `workflow-resilience`: Normalize durable-checkpoint and safe-resume requirements.

## Impact

- **Specifications:** Delta specifications for all 17 existing capabilities; after approval and application, the corresponding `openspec/specs/*/spec.md` files.
- **Validation:** Removes the existing RFC 2119 warnings so `openspec validate --all --strict` can become the project-wide completion gate.
- **Runtime:** No impact. Application code, tests, dependencies, public contracts, persistence and deployed behavior remain unchanged.
- **Governance:** Existing FRD traceability and architecture invariants remain authoritative and unchanged.
