## ADDED Requirements

### Requirement: Phase 006 Model Gateway authority boundary
FRD reference: FR-ARC-001, FR-ARC-006, FR-ARC-007, FR-ARC-011, FR-AIP-001

Phase 006 AI-assisted classification SHALL use the Model Gateway for model access while authoritative facts, deterministic policy/rule outcomes, human decisions, communications and material financial outcomes remain owned by their designated capabilities.

#### Scenario: Model Gateway does not own banking facts
- **GIVEN** classification receives case text, references and provider-derived context
- **WHEN** the Model Gateway returns a classification result
- **THEN** the result can classify category and confidence only
- **AND** it cannot replace provider facts, alter policy applicability, execute rules, approve communication or authorize money movement

#### Scenario: Phase 006 exposes no financial posting path
- **GIVEN** Phase 006 workflow, classification and Model Gateway code is deployed
- **WHEN** supported endpoints, node allow-lists, provider adapters and gateway tools are inspected
- **THEN** no refund, credit, debit, chargeback, settlement-posting or material money-movement operation is available to AI-assisted classification
- **AND** any material outcome still requires a later approved human-decision capability

#### Scenario: Business capabilities cannot bypass gateway
- **GIVEN** a business or workflow capability requires model execution
- **WHEN** architecture-boundary validation inspects imports and invocation paths
- **THEN** direct model-provider SDK usage outside the Model Gateway is rejected
- **AND** the approved path remains capability service to Model Gateway to provider adapter
