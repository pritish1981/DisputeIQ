# DisputeIQ Source-of-Truth Policy

The FRD in this folder is the program-level source of truth for the 8-week DisputeIQ implementation.

OpenSpec is the executable specification layer derived from the FRD.

## Change-control rule

If implementation discovers a required behavioral change:

1. Do not silently change the code.
2. Record the proposed change in OpenSpec.
3. Identify the affected FRD requirement/use-case/GWT scenario.
4. Review the impact.
5. Update the FRD and OpenSpec contract together if the behavior is approved.
6. Only then implement the revised behavior.

This keeps FRD → OpenSpec → code → test traceability intact.
