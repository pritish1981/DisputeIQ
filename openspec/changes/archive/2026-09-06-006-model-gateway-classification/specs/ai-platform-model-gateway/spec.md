## MODIFIED Requirements

### Requirement: Central model gateway
FRD reference: FR-AIP-001, FR-AIP-002, FR-ARC-007

The platform SHALL route every model request from an approved AI-assisted capability through the Model Gateway, SHALL use provider-neutral request and response contracts, and SHALL prohibit direct provider SDK calls from business or workflow capabilities.

#### Scenario: AI capability invokes a model
- **GIVEN** an approved AI-assisted capability requires an LLM
- **WHEN** the capability makes a model request
- **THEN** the request flows through the Model Gateway
- **AND** direct provider SDK calls from business capabilities are prohibited
- **AND** the capability receives a provider-neutral response contract rather than a provider SDK object

#### Scenario: Direct provider call is blocked
- **GIVEN** workflow, case, policy, classification, recommendation, communication or rules code attempts to invoke an LLM provider SDK directly
- **WHEN** architecture-boundary validation runs
- **THEN** the validation fails before the change is accepted
- **AND** approved model access remains available only through the Model Gateway contract

### Requirement: Structured response validation
FRD reference: FR-AIP-004

The platform SHALL validate every structured model response against its versioned schema before the response can mutate workflow state or emit an automated continuation signal.

#### Scenario: Model returns malformed structured output
- **GIVEN** an AI capability expects a versioned schema
- **WHEN** the model response fails schema validation
- **THEN** the response does not mutate workflow state
- **AND** bounded retry or governed fallback occurs
- **AND** the validation failure is visible with model, prompt, schema and correlation metadata

#### Scenario: Model returns valid structured output
- **GIVEN** an AI capability expects a versioned schema
- **WHEN** the model response passes schema validation
- **THEN** only the validated structured fields are available to the invoking capability
- **AND** raw provider payloads, hidden reasoning and provider-specific metadata do not become authoritative workflow facts

### Requirement: AI kill switch
FRD reference: FR-AIP-006

The platform SHALL provide an operator-controlled AI kill switch that safely bypasses AI execution and routes affected cases to configured manual handling without calling a model provider.

#### Scenario: AI processing disabled
- **GIVEN** an operator enables the AI kill switch
- **WHEN** a new or in-flight case reaches an AI-assisted capability
- **THEN** AI execution is bypassed safely
- **AND** the case is routed to configured manual handling
- **AND** no model provider request is sent

#### Scenario: Kill switch event is traceable
- **GIVEN** the AI kill switch bypasses an AI-assisted capability
- **WHEN** the workflow is checkpointed or the API response is returned
- **THEN** the response and audit-visible lineage identify the bypass reason, capability, configuration version and correlation ID

## ADDED Requirements

### Requirement: Prompt and model configuration governance
FRD reference: FR-AIP-003, FR-AIP-005, FR-AUD-003, FR-OBS-005

The platform SHALL resolve model, prompt, schema, token budget, timeout, retry and fallback policy from versioned configuration before a Model Gateway request is accepted.

#### Scenario: Versioned configuration is resolved
- **GIVEN** an approved AI-assisted capability requests classification
- **WHEN** the Model Gateway accepts the request
- **THEN** the accepted request records model routing policy version, prompt/template version, response schema version, token budget, timeout, retry limit and fallback policy
- **AND** those versions are available for audit reconstruction and evaluation

#### Scenario: Missing or disabled configuration fails closed
- **GIVEN** required model, prompt, schema or routing configuration is missing or disabled
- **WHEN** an AI-assisted capability requests model execution
- **THEN** the Model Gateway rejects the request with a governed fallback reason
- **AND** automated workflow progression pauses instead of using an unversioned prompt or default provider

### Requirement: Token, data policy and provider fallback controls
FRD reference: FR-AIP-001, FR-AIP-005, FR-AIP-006, FR-SEC-006

The Model Gateway SHALL enforce configured token budgets, data policy checks, timeouts, retries and provider fallback before returning an accepted AI result.

#### Scenario: Request exceeds token budget
- **GIVEN** an AI-assisted capability submits model input that exceeds its configured token budget
- **WHEN** the Model Gateway evaluates the request
- **THEN** the request is rejected or reduced through an approved policy before provider execution
- **AND** the token-control outcome is recorded with correlation metadata

#### Scenario: Provider fallback is used
- **GIVEN** the primary configured provider times out or returns a retriable provider error
- **WHEN** fallback policy permits an alternate provider
- **THEN** the Model Gateway retries or falls back within the configured limits
- **AND** the response records primary provider outcome, fallback provider reference, attempt count and final status
