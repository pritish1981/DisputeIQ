## ADDED Requirements

### Requirement: Policy corpus promotion evaluation
FRD reference: FR-OBS-005, FR-OBS-006, FR-POL-008

The platform SHALL run mandatory retrieval, citation and corpus-integrity regression evaluations before promoting a new policy corpus, embedding index or retrieval-index version.

#### Scenario: Promotion evaluation passes
- **GIVEN** a candidate policy corpus or reindex run has completed ingestion and indexing
- **WHEN** promotion evaluation runs
- **THEN** retrieval quality, citation correctness, metadata integrity and stale-policy exclusion checks are evaluated against configured thresholds
- **AND** passing results are recorded with corpus version, index version and correlation ID

#### Scenario: Promotion evaluation fails
- **GIVEN** a candidate policy corpus or reindex run fails a mandatory threshold
- **WHEN** promotion is requested
- **THEN** promotion is denied with a structured evaluation failure
- **AND** the failure is visible in operational evaluation records
