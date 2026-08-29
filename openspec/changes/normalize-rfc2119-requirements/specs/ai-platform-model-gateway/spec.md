## MODIFIED Requirements

### Requirement: Central model gateway
FRD reference: FR-AIP-001, FR-ARC-007

The platform SHALL route every model request from an approved AI-assisted capability through the Model Gateway and prohibit direct provider SDK calls from business capabilities.

#### Scenario: AI capability invokes a model
- GIVEN an approved AI-assisted capability requires an LLM
- WHEN the capability makes a model request
- THEN the request flows through the Model Gateway
- AND direct provider SDK calls from business capabilities are prohibited

### Requirement: Structured response validation
FRD reference: FR-AIP-004

The platform SHALL validate every structured model response against its versioned schema before the response can mutate workflow state.

#### Scenario: Model returns malformed structured output
- GIVEN an AI capability expects a versioned schema
- WHEN the model response fails schema validation
- THEN the response does not mutate workflow state
- AND bounded retry or governed fallback occurs

### Requirement: AI kill switch
FRD reference: FR-AIP-006

The platform SHALL provide an operator-controlled AI kill switch that safely bypasses AI execution and routes affected cases to configured manual handling.

#### Scenario: AI processing disabled
- GIVEN an operator enables the AI kill switch
- WHEN a new or in-flight case reaches an AI-assisted capability
- THEN AI execution is bypassed safely
- AND the case is routed to configured manual handling
