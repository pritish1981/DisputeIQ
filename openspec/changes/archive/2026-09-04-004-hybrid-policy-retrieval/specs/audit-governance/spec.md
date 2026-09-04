## ADDED Requirements

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
