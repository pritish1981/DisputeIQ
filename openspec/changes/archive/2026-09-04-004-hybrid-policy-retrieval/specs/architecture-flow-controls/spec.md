## ADDED Requirements

### Requirement: Step 5 controlled policy resolution boundary
FRD reference: FR-ARC-004, FR-POL-003, FR-POL-004, FR-POL-006

The platform SHALL keep Step 5 policy resolution as a controlled retrieval boundary where deterministic eligibility executes before retrieval and low-confidence outcomes route to policy review.

#### Scenario: Eligibility precedes retrieval in Step 5
- **GIVEN** policy context is required for a dispute
- **WHEN** Step 5 policy resolution begins
- **THEN** deterministic applicability filters execute before lexical, vector or reranking operations
- **AND** retrieval cannot include chunks excluded by status, effective date, product, channel, jurisdiction or configured applicability metadata

#### Scenario: Policy resolution does not decide material outcome
- **GIVEN** policy retrieval returns applicable cited context
- **WHEN** Step 5 policy resolution completes
- **THEN** the result contains policy context, citations and confidence signals only
- **AND** no material financial outcome, recommendation, customer communication or posting operation is executed by policy retrieval

#### Scenario: Low-confidence policy resolution routes to policy review
- **GIVEN** policy retrieval is missing, ambiguous, uncited or below threshold
- **WHEN** Step 5 policy resolution completes
- **THEN** automated continuation is stopped with a policy-review HITL signal
- **AND** later workflow stages cannot treat the missing policy context as approved policy authority
