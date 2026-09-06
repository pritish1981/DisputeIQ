# Phase 006 Model Gateway and Classification Gap Review

Phase 006 follows FRD v3.1 `FR-CLS-001`, `FR-CLS-002`, `FR-CLS-003`, `FR-CLS-004`, `FR-AIP-001`, `FR-AIP-002`, `FR-AIP-003`, `FR-AIP-004`, `FR-AIP-005`, `FR-AIP-006`, `FR-AUD-003`, `FR-AUD-004`, `FR-OBS-001`, `FR-OBS-002`, `FR-OBS-005`, `FR-OBS-006`, `FR-ARC-001`, `FR-ARC-006`, `FR-ARC-007`, `FR-ARC-011` and `FR-ARC-012`.

The implemented scope adds the first Model Gateway-backed AI-assisted capability: classification for duplicate-card, failed-UPI and ATM debit-without-cash dispute descriptions. The gateway uses provider-neutral contracts, versioned prompt/schema/route metadata, token/data-policy checks, fallback metadata, structured response validation, kill-switch bypass, audit-visible workflow lineage and correlated telemetry. Local validation uses a deterministic provider adapter behind the gateway, so no real model credentials are required.

Recommendation generation, evidence-analysis summarization, durable HITL task lifecycle, customer communication, final case decisioning and financial posting remain out of scope. Authoritative banking facts still come from read-only synthetic providers; policy applicability/retrieval, evidence completeness and downstream continuation gates remain deterministic.

## Existing State Reviewed

- Phase 005 workflow graph used deterministic duplicate-card classification and stopped before Model Gateway execution.
- Workflow runs/checkpoints already persisted compact state, side-effect keys, interrupt metadata and telemetry in PostgreSQL.
- Architecture-boundary tests already prohibited direct provider SDK calls and autonomous financial surfaces in earlier phases.
- Long-lived specs already declared central Model Gateway and classification intent, but did not yet define Phase 006 executable gateway/classification behavior.

## Implementation Summary

- Added Model Gateway and classification schemas for route, prompt, provider result, gateway response, telemetry, classification input/output and decision metadata.
- Added configuration defaults for AI kill switch, classification threshold, token budget, timeout and retry controls.
- Added deterministic local classification provider behind the Model Gateway for repeatable duplicate-card, failed-UPI, ATM, low-confidence, unsupported, malformed and fallback paths.
- Added Classification Service with deterministic confidence, unsupported-category, malformed-output, provider-failure, missing-config and kill-switch gates.
- Updated LangGraph classification node to invoke the Classification Service through the Model Gateway, checkpoint compact classification lineage and stop downstream execution on manual-classification signals.
- Updated workflow audit metadata and telemetry to include classification prompt/schema/route versions, confidence, provider route reference, token usage, fallback, kill-switch status and evaluation metadata.
- Expanded Case API dispute type validation to accept the three FRD MVP categories while preserving structured rejection for unknown dispute types.

## Validation Evidence

- `uv run python -m app.classification_eval`: passed with duplicate-card, failed-UPI, ATM, unsupported, low-confidence, kill-switch, fallback and malformed-output outcomes.
- `uv run python -m app.workflow_smoke`: passed against local PostgreSQL with `status: CONTROLLED_STOP`, `current_node: controlled_stop`, `state_version: 3`, `checkpoint_seq: 2`, accepted duplicate-card classification, `classification-output-v1`, `classification-router-v1`, `model-route-classification-v1`, provider route `deterministic-local`, token usage and correlation telemetry.
- `uv run ruff check .`: passed.
- `uv run mypy app tests`: passed with no issues in 46 source files.
- `uv run pytest`: `76 passed`.
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate 006-model-gateway-classification --type change --strict`: passed.
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`: `18 passed, 0 failed`.
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`: `19 passed, 1 failed` because the separate active `normalize-rfc2119-requirements` change still fails independently of Phase 006.

## Archive Evidence

- `npx.cmd -y @fission-ai/openspec@1.10.0 archive 006-model-gateway-classification --yes`: archived as `openspec/changes/archive/2026-09-06-006-model-gateway-classification`.
- Archive sync applied 10 added and 6 modified requirements across `ai-platform-model-gateway`, `architecture-flow-controls`, `audit-governance`, `classification-and-routing`, `observability-evaluation`, `security-privacy` and `workflow-orchestration`.
- Post-archive `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`: `18 passed, 0 failed`.
- Post-archive `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`: `18 passed, 1 failed` because the separate active `normalize-rfc2119-requirements` change still fails independently of Phase 006.

## Boundary Confirmation

- No direct OpenAI, Azure OpenAI, Anthropic or Bedrock SDK calls are used by business, workflow, policy, classification, recommendation or communication code.
- Model access is available only through the Model Gateway contract.
- No recommendation service, communication service, durable HITL task lifecycle, final decision command, refund, credit, debit, chargeback or settlement-posting operation is introduced.
- Workflow state rejects raw provider payloads, hidden reasoning, secrets, tokens, evidence binaries and oversized model content.
