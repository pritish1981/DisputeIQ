## ADDED Requirements

### Requirement: Versioned explainable confidence computation
FRD reference: FR-CNF-001, FR-CNF-002, FR-CNF-004, FR-ARC-006

The platform SHALL compute governed confidence using a pinned formula, normalization, rounding, weights, penalties and thresholds over classification, evidence completeness, policy retrieval, deterministic rule certainty, contextual conflicts and provider/tool failures, and expose each factor with its source reference and contribution.

#### Scenario: Confidence is reproducible and inspectable
- **GIVEN** valid pinned signal inputs and confidence configuration
- **WHEN** evaluation runs repeatedly
- **THEN** the same component contributions, aggregate and threshold decision are returned
- **AND** authorized API/UI readers can inspect raw signals, versions, penalties and reasons
- **AND** classification confidence is one recorded input, not the authoritative case score

#### Scenario: Adverse rule outcome is not uncertainty
- **GIVEN** an applicable rule deterministically returns FAIL from complete facts
- **WHEN** rule certainty is aggregated
- **THEN** the rule counts as determinate
- **AND** its adverse disposition remains distinct from confidence in that disposition

#### Scenario: Missing or invalid signals cannot inflate confidence
- **GIVEN** a required signal is absent, nonfinite, out of range or has invalid provenance
- **WHEN** confidence is evaluated
- **THEN** the unknown component and conservative diagnostic contribution are recorded without redistributing its weight
- **AND** automated readiness is blocked for review

#### Scenario: Missing formula fails closed
- **GIVEN** a compatible approved formula or threshold version cannot be resolved
- **WHEN** confidence evaluation is attempted
- **THEN** no authoritative successful score is produced
- **AND** configuration review is required

### Requirement: Hard gates precede confidence readiness
FRD reference: FR-CNF-003, FR-ARC-003, FR-ARC-005, FR-ARC-006; UC-EXC-008

The platform SHALL block readiness for mandatory evidence failure, unaccepted classification, insufficient policy authority, mandatory rule indeterminacy/error, blocking contextual conflict or required provider failure regardless of aggregate confidence, and SHALL create a durable supervisor/manual-review request when the confidence/risk gate requires review.

#### Scenario: High score cannot override mandatory gates
- **GIVEN** an aggregate above threshold and an unresolved mandatory gate
- **WHEN** readiness is calculated
- **THEN** the result remains blocked with every applicable gate reason
- **AND** no weighted score or client override can authorize progression

#### Scenario: Threshold boundary and escalation
- **GIVEN** all mandatory gates pass and a valid governed score exists
- **WHEN** the score is compared with its pinned minimum threshold
- **THEN** a score below the threshold creates supervisor review and pauses the workflow
- **AND** equality or a higher score permits only the configured recommendation boundary

#### Scenario: Threshold update preserves earlier evaluation
- **GIVEN** an existing confidence result and newly activated thresholds
- **WHEN** that existing evaluation is read or retried
- **THEN** its score and threshold decision remain unchanged
- **AND** applying new thresholds requires an explicit linked re-evaluation
