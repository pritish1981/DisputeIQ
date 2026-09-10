## ADDED Requirements

### Requirement: Governed rule registry and rule-set versions
FRD reference: FR-RUL-002, FR-RUL-004, FR-RUL-005

The platform SHALL resolve a uniquely approved environment/effective-dated rule set whose immutable version identifies every rule ID/version, parameter, execution order and policy/configuration reference; activation SHALL require successful affected-scenario regression evidence.

#### Scenario: Approved rule set is pinned
- **GIVEN** a compatible approved rule set exists for the case context
- **WHEN** a new evaluation is created
- **THEN** the rule set, members, parameters and content hashes are pinned
- **AND** later configuration activation does not change that evaluation

#### Scenario: Invalid registry content is rejected
- **GIVEN** an unknown rule, conflicting version payload, invalid parameter, ambiguous effective match or failed regression result
- **WHEN** registration or evaluation is attempted
- **THEN** configuration is rejected or execution stops with a configuration reason
- **AND** no implicit latest-version fallback or dynamic user-supplied code is executed

### Requirement: Deterministic duplicate-card evaluation
FRD reference: FR-RUL-001, FR-RUL-002, FR-ARC-002, FR-ARC-005; UC-E2E-001

The Rules Engine SHALL evaluate eligibility, transaction timelines, mandatory evidence, duplicate transaction predicates and existing remediation using authoritative normalized facts and pinned policy/configuration. It SHALL return repeatable PASS, FAIL, NOT_APPLICABLE, INDETERMINATE or ERROR outcomes and a deterministic disposition candidate without finalizing the case.

#### Scenario: Two authoritative transactions support duplication
- **GIVEN** two distinct authoritative transactions meet the configured account, merchant, currency, amount, time, settlement, evidence and remediation predicates
- **WHEN** the pinned rule set executes
- **THEN** the result includes a DUPLICATE_SUPPORTED candidate and every supporting rule/reason reference
- **AND** it neither approves a financial outcome nor invokes posting tools

#### Scenario: Possible duplicate reference is insufficient
- **GIVEN** the first transaction names a possible duplicate but the second authoritative transaction is unavailable
- **WHEN** evaluation runs
- **THEN** duplication is indeterminate with a missing-authoritative-facts reason
- **AND** a model or customer allegation cannot make the result determinate

#### Scenario: Adverse findings remain determinate
- **GIVEN** complete facts show a nonmatching pair, an exceeded filing window or completed remediation
- **WHEN** configured rules execute
- **THEN** the corresponding adverse result and DUPLICATE_NOT_SUPPORTED or ALREADY_REMEDIATED candidate are retained
- **AND** a determinate FAIL is not represented as an execution error

#### Scenario: Timeline boundaries are reproducible
- **GIVEN** transaction and submission timestamps are at, below or above configured boundaries
- **WHEN** the rules execute against identical normalized facts and versions
- **THEN** exact inclusive boundary outcomes follow pinned parameters
- **AND** the current wall clock, input ordering and retry count do not change the result

### Requirement: Rule exceptions and execution lineage
FRD reference: FR-RUL-002, FR-RUL-003, FR-ARC-005; UC-EXC-007

The platform SHALL persist every rule result with rule ID/version, outcome, reason code, fact references, policy/configuration references and facts hash, and SHALL route mandatory indeterminate/error results to durable manual review without LLM fallback.

#### Scenario: Rule execution fails
- **GIVEN** a rule raises an exception or mandatory inputs are inconsistent
- **WHEN** execution is recorded
- **THEN** the failed rule and safe reason are retained with REVIEW_REQUIRED
- **AND** a durable manual-review request blocks recommendation readiness

#### Scenario: Rule result is distinguishable from AI rationale
- **GIVEN** an authorized reader inspects an evaluation through API or UI
- **WHEN** rule results are displayed
- **THEN** deterministic outcomes, versions and reasons are explicitly labeled
- **AND** AI classification or any later rationale cannot overwrite or appear as authoritative rule results
