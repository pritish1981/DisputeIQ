## ADDED Requirements

### Requirement: Phase 007 deterministic progression
FRD reference: FR-WFL-001, FR-ARC-001, FR-ARC-003, FR-ARC-004, FR-ARC-005, FR-ARC-006

The platform SHALL support an explicitly versioned Phase 007 duplicate-card graph that pins controls, assesses evidence, resolves eligible cited policy, executes deterministic rules and computes governed confidence, stopping at the recommendation/human-decision boundary when ready.

#### Scenario: Duplicate-card reaches the Phase 007 exit
- **GIVEN** a submitted duplicate-card case with accepted classification, authoritative paired transaction context, complete evidence and applicable approved policy
- **WHEN** the Phase 007 graph executes and its gates pass
- **THEN** the workflow records a deterministic disposition candidate, rule results and governed confidence
- **AND** it reaches CONTROLLED_STOP with reason deterministic_disposition_ready and pinned evidence contract, policy, rules and thresholds
- **AND** no recommendation model, human approval, customer message or financial posting executes

#### Scenario: Evidence and policy gates preserve ordering
- **GIVEN** mandatory evidence or applicable policy is unavailable
- **WHEN** the Phase 007 workflow reaches the relevant gate
- **THEN** it persists the corresponding request and waiting checkpoint
- **AND** downstream rules and readiness cannot proceed with assumed evidence or policy

#### Scenario: Existing checkpoint compatibility
- **GIVEN** a persisted Phase 005 or Phase 006 graph version
- **WHEN** it is inspected or resumed
- **THEN** its existing semantics and readable result lineage are preserved
- **AND** Phase 007 rules are not silently executed under the old graph version

### Requirement: Immutable evaluation bundle and controlled re-evaluation
FRD reference: FR-WFL-002, FR-WFL-005, FR-AUD-003, FR-AUD-004, FR-ARC-011, FR-ARC-012

The platform SHALL persist immutable evaluation bundles with facts/evidence snapshots and hashes, evaluation time, classification provenance and all consumed control/policy versions; retries SHALL reuse accepted results and changed inputs SHALL produce explicitly linked re-evaluations.

#### Scenario: Same accepted evaluation is replayed
- **GIVEN** an accepted evaluation and an identical idempotent command
- **WHEN** the command is replayed after restart
- **THEN** the original evaluation and result references are returned
- **AND** no duplicate evaluation, model invocation, request or business audit event is created

#### Scenario: Evidence change triggers linked re-evaluation
- **GIVEN** new validated evidence and an authorized current-version resume command
- **WHEN** the evaluation is repeated
- **THEN** a new snapshot and evaluation time are pinned with a link to the prior evaluation
- **AND** affected downstream results are recomputed while the prior bundle remains immutable

#### Scenario: Stale or forged re-evaluation is rejected
- **GIVEN** a stale workflow version, conflicting idempotency payload or caller-supplied rule/score/approval override
- **WHEN** resume or re-evaluation is submitted
- **THEN** the platform returns a structured conflict or validation/access error
- **AND** no gate is bypassed or existing evaluation overwritten

### Requirement: Durable control review requests
FRD reference: FR-EVD-004, FR-CNF-003, FR-WFL-004, FR-ARC-006

The platform SHALL persist typed evidence, policy, rule/manual and supervisor-review requests with their blocked evaluation and checkpoint, including role, reasons and resume requirements, without treating request creation as human approval.

#### Scenario: Rule or confidence review is durable
- **GIVEN** a mandatory rule exception or low-confidence outcome
- **WHEN** the workflow pauses
- **THEN** its WAITING_RULE_REVIEW or WAITING_SUPERVISOR_REVIEW state and request survive process restart
- **AND** Phase 007 cannot resolve that request through an unimplemented reviewer-approval action

#### Scenario: Review persistence fails
- **GIVEN** a control transition needs a request, result, checkpoint and audit event
- **WHEN** any required write fails
- **THEN** the transition is not accepted and no partially successful progression is exposed

### Requirement: Authorized control evaluation visibility
FRD reference: FR-CNF-004, FR-RUL-003, FR-AUD-003

The platform SHALL expose scoped evaluation history and details containing evidence assessments, policy eligibility, deterministic rule results, confidence factors, pinned versions and review reasons to authorized readers.

#### Scenario: Evaluation details are inspectable
- **GIVEN** an authorized reader and a workflow with control evaluations
- **WHEN** history or details are requested
- **THEN** compact result and provenance references are returned in stable order
- **AND** raw evidence binaries, secrets and unrestricted provider payloads are absent

#### Scenario: Evaluation from another workflow is requested
- **GIVEN** an unknown or differently scoped evaluation ID
- **WHEN** its details are requested through a workflow
- **THEN** a structured not-found/access response is returned without leaking the other case's data
