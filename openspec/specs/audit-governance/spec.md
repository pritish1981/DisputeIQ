# Audit Governance and Explainability

## Purpose
Define append-only business audit, version traceability and reconstruction.

## Requirements

### Requirement: Immutable material events
FRD reference: FR-AUD-001

The platform SHALL record every material case lifecycle action as an append-only business audit event independent of application logs.

#### Scenario: Material lifecycle action occurs
- **GIVEN** a material case lifecycle action completes
- **WHEN** audit recording executes
- **THEN** an append-only business audit event is written independently of application logs

#### Scenario: Phase 002 audit failure blocks accepted mutation
- **GIVEN** a material Phase 002 case mutation requires an audit event
- **WHEN** the audit event cannot be persisted in the same accepted operation boundary
- **THEN** the mutation is not reported as successful
- **AND** no accepted case or evidence metadata mutation is left without its required business audit event

### Requirement: Decision reconstruction
FRD reference: FR-AUD-003, FR-AUD-004

The platform SHALL retain sufficient evidence, policy, rule, AI configuration, recommendation and human-decision lineage to reconstruct a completed case.

#### Scenario: Auditor reconstructs completed case
- **GIVEN** an authorized auditor selects a closed case
- **WHEN** the audit view is reconstructed
- **THEN** evidence, policy, rules, AI configuration, recommendation and human decision are traceable

### Requirement: Baseline audit event contract
FRD reference: FR-AUD-002

Phase 002 business audit events SHALL include event ID, case ID, actor, timestamp, event type, source, correlation ID, relevant version metadata, and object references needed for case reconstruction.

#### Scenario: Case creation audit event
- **GIVEN** a synthetic duplicate-card case is created
- **WHEN** the `CASE_CREATED` event is persisted
- **THEN** the audit event includes event ID, case ID, actor, timestamp, event type, source, correlation ID, state version, and relevant request/provider metadata references

#### Scenario: Evidence metadata audit event
- **GIVEN** evidence metadata is registered for a case
- **WHEN** the material evidence event is persisted
- **THEN** the audit event includes event ID, case ID, evidence ID or object reference, actor, timestamp, event type, source, correlation ID, and state version

### Requirement: Audit-linked replay visibility
FRD reference: FR-CAS-004, FR-AUD-001, FR-AUD-002

The platform SHALL make safe idempotent replays observable without duplicating material business audit events.

#### Scenario: Idempotent replay does not duplicate material event
- **GIVEN** a create-case request has already emitted `CASE_CREATED`
- **WHEN** the same logical request is replayed with the same idempotency key
- **THEN** the original case result is returned
- **AND** no second `CASE_CREATED` audit event is emitted
- **AND** replay metadata is available for operational diagnostics

### Requirement: Policy ingestion audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-POL-001, FR-POL-008

The platform SHALL record controlled policy ingestion, rejection, reindex and corpus-promotion decisions as append-only business audit events with enough lineage to reconstruct corpus membership.

#### Scenario: Policy ingestion event is recorded
- **GIVEN** a policy document ingestion request is accepted, rejected or fails validation
- **WHEN** the ingestion decision is finalized
- **THEN** an append-only audit event records actor, timestamp, event type, source, correlation ID, document ID, version, checksum, ingestion run ID and decision status

#### Scenario: Corpus promotion event is recorded
- **GIVEN** a policy corpus or reindex run is promoted or promotion is blocked
- **WHEN** the promotion decision is finalized
- **THEN** an append-only audit event records the corpus version, index version, evaluation result, actor, timestamp and correlation ID
- **AND** the event can be linked to the documents and chunks included in or excluded from the candidate corpus

### Requirement: Policy retrieval audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-POL-005, FR-POL-006

The platform SHALL record policy retrieval decisions and policy-review abstentions as append-only audit events with enough lineage to reconstruct the policy context used or refused.

#### Scenario: Policy retrieval event is recorded
- **GIVEN** policy retrieval returns ranked context for a case or validation request
- **WHEN** the retrieval decision is finalized
- **THEN** an append-only audit event records actor or service, timestamp, event type, source, correlation ID, corpus version, index version, retrieval configuration version, selected chunk IDs, document IDs, versions, sections and confidence outcome

#### Scenario: Policy retrieval abstention is recorded
- **GIVEN** policy retrieval abstains because of missing corpus, no eligible candidates, ambiguity, low confidence or missing citations
- **WHEN** the abstention decision is finalized
- **THEN** an append-only audit event records the abstention reason, candidate/result counts, actor or service, timestamp, source, correlation ID and required policy-review HITL signal

#### Scenario: Audit failure blocks accepted retrieval decision
- **GIVEN** a policy retrieval decision requires an audit event
- **WHEN** the audit event cannot be persisted in the accepted operation boundary
- **THEN** the retrieval decision is not reported as successful
- **AND** no automated continuation signal is emitted without the required audit event

### Requirement: Workflow audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-WFL-001, FR-ARC-012

The platform SHALL record workflow starts, node completions, checkpoints, interrupts, resumes and failures as append-only audit-visible events with enough lineage to reconstruct workflow progression.

#### Scenario: Workflow start is audited
- **GIVEN** a workflow start command is accepted
- **WHEN** the workflow run is created
- **THEN** an append-only audit-visible event records case ID, workflow ID, actor, event type, source, graph version, state version, correlation ID and timestamp

#### Scenario: Workflow interrupt is audited
- **GIVEN** workflow execution pauses for missing evidence, policy review, manual classification or manual degradation
- **WHEN** the interrupt checkpoint is persisted
- **THEN** an audit-visible event records workflow ID, node name, interrupt reason, checkpoint sequence, state version and correlation ID

#### Scenario: Workflow audit failure blocks accepted transition
- **GIVEN** a material workflow transition requires audit-visible lineage
- **WHEN** the lineage event cannot be persisted in the accepted operation boundary
- **THEN** the workflow transition is not reported as successful
- **AND** no automated continuation signal is emitted without required lineage

### Requirement: Model Gateway and classification audit lineage
FRD reference: FR-AUD-001, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-AIP-003, FR-CLS-004

The platform SHALL record Model Gateway invocations, classification outcomes, schema validation failures, kill-switch bypasses and manual-classification routing as audit-visible lineage sufficient to reconstruct AI-assisted classification behavior.

#### Scenario: Classification success is audited
- **GIVEN** AI-assisted classification succeeds with a supported category
- **WHEN** the result is accepted
- **THEN** audit-visible lineage records case ID, workflow ID when available, actor or service, event type, source, correlation ID, category, confidence, model route version, prompt version, schema version, token usage and timestamp
- **AND** raw provider payloads and hidden reasoning are not required for business audit reconstruction

#### Scenario: Classification fallback is audited
- **GIVEN** classification is bypassed, retried, falls back, fails schema validation, returns low confidence or identifies an unsupported category
- **WHEN** automated progression is paused
- **THEN** audit-visible lineage records the failure or bypass reason, attempt count, fallback outcome, configured threshold, manual-classification signal and correlation ID

#### Scenario: Audit failure blocks accepted AI transition
- **GIVEN** a classification transition requires audit-visible lineage
- **WHEN** the lineage event cannot be persisted in the accepted operation boundary
- **THEN** the classification transition is not reported as successful
- **AND** no automated continuation signal is emitted without required lineage
