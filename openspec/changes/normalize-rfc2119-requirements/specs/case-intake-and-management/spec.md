## MODIFIED Requirements

### Requirement: Idempotent mutation
FRD reference: FR-CAS-004

The platform SHALL return the original result without creating a second dispute case when a completed create request is safely replayed with the same idempotency key and logical payload.

#### Scenario: Duplicate create request
- GIVEN a prior request completed successfully with an idempotency key
- WHEN the same logical request is safely replayed with that key
- THEN a second dispute case is not created
- AND the original result is returned

#### Scenario: Idempotency key reused with different payload
- **GIVEN** a prior create-case request completed successfully with an idempotency key
- **WHEN** a caller reuses that key with a different logical payload
- **THEN** the request is rejected as an idempotency conflict
- **AND** no new case or material side effect is created
