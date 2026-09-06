## MODIFIED Requirements

### Requirement: Governed graph progression
FRD reference: FR-ARC-001, FR-ARC-002, FR-ARC-003, FR-ARC-004, FR-ARC-005, FR-ARC-008, FR-AIP-001

The platform SHALL use LangGraph to coordinate routing across bounded workflow stages while designated provider, deterministic, policy, model-gateway and human capabilities retain authority for their owned decisions and data.

#### Scenario: Duplicate-card workflow progresses through available stages
- **GIVEN** a submitted duplicate-card case has persisted authoritative context, AI-assisted classification is enabled, and a promoted applicable policy corpus exists
- **WHEN** Phase 006 workflow execution runs
- **THEN** LangGraph routes through intake, Model Gateway classification routing, authoritative-context reference capture, evidence gate and policy-context resolution
- **AND** the resulting workflow state records stage outcomes, citations or interrupt signals without finalizing a material financial outcome

#### Scenario: Later capability boundary stops progression
- **GIVEN** the workflow reaches recommendation, durable human decision, communication or financial finalization behavior that is outside Phase 006
- **WHEN** routing evaluates the next stage
- **THEN** automated progression stops with a controlled workflow status and reason
- **AND** no recommendation, customer communication, human decision, refund, credit, debit or chargeback operation is executed

## ADDED Requirements

### Requirement: Classification node uses Model Gateway
FRD reference: FR-WFL-001, FR-CLS-001, FR-CLS-002, FR-AIP-001, FR-AIP-004, FR-ARC-012

The workflow classification node SHALL invoke the classification service through the Model Gateway, checkpoint validated classification output, and interrupt safely for low confidence, unsupported category, kill-switch bypass or validation failure.

#### Scenario: Classification checkpoint is persisted
- **GIVEN** workflow classification returns a valid supported category above threshold
- **WHEN** the classification node completes
- **THEN** the workflow checkpoint records category, confidence, extracted attributes, schema version, prompt version, model routing version and correlation ID
- **AND** raw provider payloads and hidden reasoning are absent from workflow state

#### Scenario: Classification interrupt is persisted
- **GIVEN** classification is below threshold, unsupported, bypassed by kill switch or unavailable after governed fallback
- **WHEN** the classification node completes
- **THEN** the workflow is checkpointed with a manual-classification interrupt
- **AND** downstream authoritative-context, policy, rule, recommendation, communication and financial-finalization nodes do not execute automatically

#### Scenario: Idempotent resume does not duplicate classification side effects
- **GIVEN** a workflow checkpoint records an accepted classification side-effect key
- **WHEN** the workflow is retried or resumed from that checkpoint
- **THEN** the completed classification result is reused or skipped according to the checkpoint
- **AND** no duplicate model invocation, audit event or checkpoint is created for the same accepted classification side effect
