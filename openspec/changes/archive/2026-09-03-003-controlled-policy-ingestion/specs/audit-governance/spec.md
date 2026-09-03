## ADDED Requirements

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
