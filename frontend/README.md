# Frontend

React + TypeScript foundation UI for `001-platform-foundation`.

## Local Checks

From `frontend/`:

```powershell
npm install
npm run lint
npm run typecheck
npm test
npm run build
```

## Manual UI Validation

Start the backend and frontend, then verify:

- Creating the default synthetic duplicate-card case succeeds.
- The returned case shows `Submitted` status.
- The detail view shows timeline, evidence metadata, provider context, audit events, and correlation ID.
- Reusing the same idempotency key with the same request returns the same case.
- Removing a required field shows validation feedback.
- Looking up the returned case ID reloads the same foundation detail.

Reviewer task queues and human decision UI are introduced in the HITL phase, not in this foundation change.
