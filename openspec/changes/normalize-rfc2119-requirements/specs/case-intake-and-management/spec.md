## MODIFIED Requirements

### Requirement: Idempotent mutation
FRD reference: FR-CAS-004

The platform SHALL return the original result without creating a second dispute case when a completed create request is safely replayed with the same idempotency key and logical payload.

#### Scenario: Duplicate create request
- GIVEN a prior request completed successfully with an idempotency key
- WHEN the same logical request is safely replayed with that key
- THEN a second dispute case is not created
- AND the original result is returned
