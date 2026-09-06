## MODIFIED Requirements

### Requirement: Supported dispute classification
FRD reference: FR-CLS-001, FR-CLS-004, FR-AIP-001

The platform SHALL classify valid submitted disputes into the three configured MVP categories using the Model Gateway and a versioned structured output containing category, confidence and supporting extracted attributes.

#### Scenario: Supported category classified
- **GIVEN** a valid submitted dispute is eligible for AI-assisted classification
- **WHEN** classification executes
- **THEN** the request is routed through the Model Gateway
- **AND** output conforms to the versioned structured schema
- **AND** category, confidence and supporting extracted attributes are returned

#### Scenario: Duplicate-card classification is supported
- **GIVEN** a submitted dispute describes a duplicate card transaction
- **WHEN** classification succeeds above the configured threshold
- **THEN** the category is `duplicate_card_transaction`
- **AND** the classification result includes confidence, schema version, prompt version, model routing version and correlation ID

#### Scenario: Failed-UPI classification is supported
- **GIVEN** a submitted dispute describes a failed UPI transfer
- **WHEN** classification succeeds above the configured threshold
- **THEN** the category is `failed_upi_transfer`
- **AND** automated progression is allowed only if later phase prerequisites for that category are available or the workflow routes to a controlled boundary

#### Scenario: ATM debit without cash classification is supported
- **GIVEN** a submitted dispute describes an ATM debit without cash
- **WHEN** classification succeeds above the configured threshold
- **THEN** the category is `atm_debit_without_cash`
- **AND** automated progression is allowed only if later phase prerequisites for that category are available or the workflow routes to a controlled boundary

### Requirement: Low-confidence classification gate
FRD reference: FR-CLS-002

The platform SHALL pause automated progression and emit a manual-classification HITL signal when classification confidence is below the configured threshold.

#### Scenario: Classification confidence below threshold
- **GIVEN** classification confidence is below configured threshold
- **WHEN** routing evaluates the result
- **THEN** automated progression pauses
- **AND** a manual-classification HITL signal is created
- **AND** the threshold, actual confidence, category candidate and correlation ID are recorded

#### Scenario: Threshold is configuration-controlled
- **GIVEN** a classification prompt or provider response proposes a confidence threshold
- **WHEN** routing evaluates the classification result
- **THEN** the configured threshold controls continuation
- **AND** prompt text or provider output cannot lower the configured gate

## ADDED Requirements

### Requirement: Unsupported and malformed classification handling
FRD reference: FR-CLS-003, FR-CLS-004, FR-AIP-004

The platform SHALL route unsupported, malformed or schema-invalid classification outcomes to safe manual handling without hallucinating a supported category.

#### Scenario: Unsupported category returned
- **GIVEN** classification output identifies a dispute outside the three configured MVP categories
- **WHEN** routing evaluates the result
- **THEN** automated progression pauses with a manual-classification signal
- **AND** no supported category is invented

#### Scenario: Malformed classification output rejected
- **GIVEN** the model returns malformed or schema-invalid classification output
- **WHEN** classification validation executes
- **THEN** workflow state is not mutated with the invalid output
- **AND** bounded retry or governed fallback occurs
- **AND** final failure routes to manual classification

### Requirement: Classification evaluation lineage
FRD reference: FR-CLS-002, FR-OBS-005, FR-OBS-006, FR-AUD-003

The platform SHALL record classification corrections, confidence outcomes, schema versions and model/prompt configuration versions so classification behavior can be evaluated and improved.

#### Scenario: Manual correction is recorded
- **GIVEN** an authorized reviewer corrects a classification result
- **WHEN** the correction is accepted
- **THEN** the original category, corrected category, original confidence, reviewer rationale and configuration versions are available for evaluation
- **AND** the correction does not authorize a material financial outcome by itself

#### Scenario: Classification regression is evaluated
- **GIVEN** a classification prompt, model route, threshold or schema changes
- **WHEN** the classification evaluation suite runs
- **THEN** supported-category accuracy, unsupported-category routing, low-confidence routing and schema-validity checks are evaluated against configured thresholds
- **AND** failed mandatory thresholds block acceptance of the classification configuration
