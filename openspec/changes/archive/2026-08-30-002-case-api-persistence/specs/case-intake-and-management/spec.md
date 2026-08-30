## MODIFIED Requirements

### Requirement: Unique dispute case
FRD reference: FR-CAS-001

The system SHALL create a globally unique case for every accepted dispute and SHALL persist customer reference, transaction reference, optional account reference, channel, channel metadata, timestamps, dispute description, lifecycle status, correlation ID, and current state version.

#### Scenario: Valid dispute creation
- **GIVEN** an authorized caller submits a valid synthetic duplicate-card dispute to the case API
- **WHEN** the create-case request is accepted
- **THEN** a globally unique immutable case identifier is created
- **AND** the case is persisted with customer, transaction, channel, timestamp, description, status, correlation, and version fields
- **AND** a `CASE_CREATED` business audit event is emitted

#### Scenario: Case creation remains pre-orchestration
- **GIVEN** an authorized caller submits a valid synthetic duplicate-card dispute
- **WHEN** the case is created during Phase 002
- **THEN** the accepted case is persisted without starting LangGraph workflow execution
- **AND** no LLM, RAG, recommendation, HITL, communication, refund, credit, debit, or chargeback action is invoked

### Requirement: Mandatory intake validation
FRD reference: FR-CAS-002

The system SHALL validate required intake fields and supported reference formats before case persistence or workflow execution.

#### Scenario: Missing mandatory intake data
- **GIVEN** required intake data is missing
- **WHEN** the caller submits the create-case request
- **THEN** graph execution does not begin
- **AND** no case, timeline entry, evidence metadata record, provider context, or business audit event is committed
- **AND** structured field-level validation errors are returned

#### Scenario: Unsupported dispute type
- **GIVEN** a caller submits a dispute type that is not enabled for Phase 002
- **WHEN** the create-case request is validated
- **THEN** the request is rejected with a structured validation error
- **AND** no case is created

### Requirement: Idempotent mutation
FRD reference: FR-CAS-004

The platform SHALL return the original result without creating a second dispute case when a completed create request is safely replayed with the same idempotency key and logical payload.

#### Scenario: Duplicate create request
- **GIVEN** a prior create-case request completed successfully with an idempotency key
- **WHEN** the same logical request is safely replayed with that key
- **THEN** a second dispute case is not created
- **AND** the original create-case result is returned
- **AND** the replay is observable through idempotency/audit metadata without emitting a second `CASE_CREATED` event

#### Scenario: Idempotency key reused with different payload
- **GIVEN** a prior create-case request completed successfully with an idempotency key
- **WHEN** a caller reuses that key with a different logical payload
- **THEN** the request is rejected as an idempotency conflict
- **AND** no new case or material side effect is created

## ADDED Requirements

### Requirement: Case lifecycle and optimistic versioning
FRD reference: FR-CAS-003, FR-CAS-004

The platform SHALL maintain a deterministic case lifecycle status and monotonic state version for material case mutations.

#### Scenario: Case status initialized
- **GIVEN** a valid synthetic duplicate-card case is created
- **WHEN** the case is persisted
- **THEN** the case status is initialized to the configured intake/submitted status
- **AND** the initial state version is returned to the caller

#### Scenario: Optimistic locking rejects stale mutation
- **GIVEN** a case mutation requires optimistic concurrency
- **WHEN** the caller supplies an `If-Match` or equivalent expected version that does not match the current case state version
- **THEN** the mutation is rejected with a structured conflict response
- **AND** the existing case state remains unchanged

### Requirement: Case retrieval and MVP search
FRD reference: FR-CAS-001, FR-CAS-003, FR-CAS-005

The platform SHALL allow authorized callers to retrieve a case by case ID and SHALL support MVP case listing/search by operational metadata required for analyst access.

#### Scenario: Retrieve persisted case
- **GIVEN** a synthetic duplicate-card case has been created
- **WHEN** an authorized caller requests the case by case ID
- **THEN** the response contains case identity, lifecycle status, customer and transaction references, timestamps, channel metadata, correlation ID, state version, evidence metadata summary, provider context lineage, and audit-visible timeline data

#### Scenario: List or search cases by metadata
- **GIVEN** persisted cases exist for authorized operational review
- **WHEN** an authorized caller searches by supported metadata such as status, customer reference, transaction reference, channel, or opened date range
- **THEN** matching case summaries are returned in a deterministic order
- **AND** unauthorized or unsupported filters are rejected without exposing unrelated case data

### Requirement: Chronological case timeline
FRD reference: FR-CAS-005

The platform SHALL expose a chronological timeline of case, evidence, lifecycle, and audit-relevant events for each authorized case.

#### Scenario: Retrieve case timeline
- **GIVEN** a case has timeline events
- **WHEN** an authorized caller requests the case timeline
- **THEN** timeline entries are returned in chronological order
- **AND** each entry includes event identity, case ID, event type, occurred timestamp, actor/source, correlation ID, and linked audit reference when available

#### Scenario: Timeline for unknown case
- **GIVEN** no case exists for the requested case ID
- **WHEN** a caller requests its timeline
- **THEN** a structured not-found response is returned
