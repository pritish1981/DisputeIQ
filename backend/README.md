# Backend

FastAPI/Pydantic Case API and persistence implementation for `002-case-api-persistence`.

## Local Checks

From `backend/`:

```powershell
uv run ruff check .
uv run mypy app tests
uv run pytest
```

## Database

The Phase 002 migrations create durable PostgreSQL business and audit tables for:

- cases
- idempotency records
- timeline entries
- evidence metadata
- synthetic provider context
- audit events

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

Do not add LangGraph, policy RAG, Model Gateway, LLM, HITL, recommendation, communication, or financial posting behavior during this change.
