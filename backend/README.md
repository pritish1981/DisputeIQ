# Backend

FastAPI/Pydantic Case API and controlled policy ingestion implementation for
`003-controlled-policy-ingestion`.

## Local Checks

From `backend/`:

```powershell
uv run ruff check .
uv run mypy app tests
uv run pytest
```

## Database

The migrations create durable PostgreSQL business, audit, and policy corpus tables for:

- cases
- idempotency records
- timeline entries
- evidence metadata
- synthetic provider context
- audit events
- policy ingestion runs
- policy documents
- policy chunks
- policy corpus versions
- policy evaluation results
- policy audit events

Run migrations from `backend/`:

```powershell
uv run alembic upgrade head
```

## API Smoke

Start the API:

```powershell
uv run uvicorn app.main:app --reload
```

Check:

- `GET /health` returns `{"status":"ok"}`.
- `POST /api/v1/cases` creates a synthetic duplicate-card case with `Idempotency-Key`.
- Repeating the same request and key returns the original case.
- Reusing the same key with a different payload returns an idempotency conflict.
- `GET /api/v1/cases` lists and searches cases by supported operational metadata.
- `GET /api/v1/cases/{case_id}` returns versioned case detail and lineage.
- `POST/GET /api/v1/cases/{case_id}/evidence` registers and lists metadata.
- `GET /api/v1/cases/{case_id}/timeline` returns linked chronological events.
- `/api/v1/disputes` remains a deprecated compatibility surface.
- `POST /api/v1/policies/ingestions` validates, chunks, embeds, indexes, and audits approved policy documents.
- `GET /api/v1/policies/ingestions/{run_id}` returns ingestion lineage.
- `POST /api/v1/policies/promotions` runs mandatory corpus evaluation and promotes a complete candidate.
- `GET /api/v1/policies/chunks/{chunk_id}/lineage` reconstructs citation lineage.

Load synthetic policy fixtures with:

```powershell
uv run python -m app.policy_fixture_loader
```

Do not add LangGraph workflow execution, recommendation, communication, HITL decisioning,
or financial posting behavior during this change.
