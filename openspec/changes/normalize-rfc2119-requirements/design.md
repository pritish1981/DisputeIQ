## Context

The 17 long-lived DisputeIQ capability specifications contain 35 requirements whose GWT scenarios are valid but whose requirement bodies omit an explicit RFC 2119 keyword. OpenSpec strict validation therefore reports warnings for those requirements and prevents project-wide strict validation from serving as the completion evidence for platform-foundation task 8.5.

This change is specification normalization only. The FRD, approved architecture artifacts and existing scenarios remain authoritative. No runtime behavior needs to change because the scenarios already express the required outcomes.

## Goals and Non-Goals

**Goals:**

- Make every affected requirement explicitly normative with `SHALL`, `SHALL NOT`, `MUST` or `MUST NOT` language.
- Preserve requirement titles, FRD references, scenarios and architecture ownership boundaries.
- Make project-wide strict OpenSpec validation pass after the approved deltas are synced.
- Keep the normalization mechanically reviewable and auditable.

**Non-Goals:**

- Change application behavior, APIs, schemas, persistence, dependencies or tests.
- Add, remove, rename or reinterpret capabilities or requirements.
- Expand the product scope beyond the existing FRD and architecture.
- Complete platform-foundation task 8.5 before project-wide strict validation succeeds.

## Decisions

### Add one normative statement to each affected requirement

Each affected requirement receives one concise normative sentence using RFC 2119 language. The sentence restates the behavior already established by its scenario and does not introduce a new outcome.

This approach is preferred over changing the scenario bullets because OpenSpec validates normative requirement prose, while the existing scenarios are already the accepted behavioral evidence.

### Preserve traceability and scenarios exactly

Requirement titles, FRD references, scenario titles and all GIVEN/WHEN/THEN/AND bullets remain unchanged. Only the missing requirement-body sentence is added. This creates a narrow diff and allows reviewers to compare the normative sentence directly with the unchanged scenario.

### Keep the change specification-only

No application or test files are in scope. The later apply phase updates the long-lived OpenSpec documents and runs validation; it does not modify runtime implementation.

### Use strict validation as the completion gate

The change must pass strict change validation before application. After approval and synchronization, `openspec validate --all --strict` must pass before platform-foundation task 8.5 can be marked complete.

## Risks and Mitigations

- **Risk: Normative wording subtly broadens or narrows behavior.** Mitigation: retain every original scenario and use wording that directly restates its outcomes.
- **Risk: A capability or warning is omitted.** Mitigation: verify 17 delta spec files, 35 modified requirements and 35 normative statements against the strict-validation baseline.
- **Risk: Platform task 8.5 is closed prematurely.** Mitigation: keep it open until the normalized long-lived specs pass project-wide strict validation.

## Migration Plan

1. Review and approve this proposal, design, delta specs and task list.
2. Apply the approved delta specifications to the 17 long-lived capability specs.
3. Run change-level and project-wide strict OpenSpec validation.
4. Mark platform-foundation task 8.5 complete only after the project-wide command passes.

Rollback consists of reverting the specification-only wording changes. No data, application or deployment rollback is required.
