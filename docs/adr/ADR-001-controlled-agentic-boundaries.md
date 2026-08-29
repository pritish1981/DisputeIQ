# ADR-001: Controlled Agentic AI Boundaries

## Status
Accepted baseline.

## Decision

DisputeIQ uses LangGraph for stateful orchestration while keeping authoritative banking facts, deterministic policy/rules and material decisions outside autonomous LLM control.

## Consequences

- AI capabilities are bounded and schema-driven.
- Provider adapters are read-only by default.
- Deterministic services remain independently testable.
- HITL is mandatory for material outcomes.
- All LLM calls pass through the Model Gateway.
- Audit reconstruction is a first-class requirement.
