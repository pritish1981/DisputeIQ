# DisputeIQ Codex Engineering Contract

## Mandatory Source Hierarchy

1. `docs/source-of-truth/DisputeIQ_FRD_v3.0_8Week_OpenSpec_GWT_Reference_TOC_Fixed.docx`
2. Approved architecture/sequence/data-flow artifacts in `docs/architecture/`
3. `openspec/specs/`
4. The currently active `openspec/changes/<change-id>/`
5. Code and tests

If a lower-level source conflicts with a higher-level source, stop and report the conflict. Do not silently reinterpret the requirement.

## OpenSpec Rule

Do not begin implementation without an active OpenSpec change containing reviewed proposal/spec/design/tasks artifacts.

## Architecture Invariants

- LangGraph is an orchestrator, not an autonomous agent swarm.
- AI does not own authoritative financial facts.
- Read-oriented provider interfaces own banking data acquisition.
- Policy eligibility/applicability is deterministic before RAG.
- Evidence completeness and mandatory evidence gates are deterministic.
- Core business/eligibility/timeline rules execute in the deterministic Rules Engine.
- Human decision is mandatory for material financial outcomes.
- Recommendation/communication capabilities cannot invoke financial posting tools.
- All model calls go through the Model Gateway.
- Every AI structured output is schema validated before mutating workflow state.
- All material transitions emit business audit events.
- PostgreSQL is durable authority for business state and graph checkpoints.
- Redis is transient cache/queue/lock only.
- No long-term autonomous conversational memory in the decision path.

## Codex Working Method

Before code:
1. Read the active OpenSpec change and relevant long-lived specs.
2. Identify affected FRD requirement IDs.
3. Produce an implementation plan.
4. Wait for review/approval before implementation.

During code:
- Implement only active-change tasks.
- Keep deterministic and AI responsibilities separated.
- Add tests alongside behavior.
- Preserve correlation IDs and audit behavior.
- Do not introduce future-phase dependencies unless approved.

Before completion:
- Run relevant unit/integration/graph/RAG/AI/security tests.
- Run `openspec validate --all --strict`.
- Report files changed, tests run, remaining risks, and any deviation from the approved spec.
