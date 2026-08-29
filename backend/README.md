# Backend

FastAPI/Pydantic foundation for `001-platform-foundation`.

## Local Checks

From `backend/`:

```powershell
uv run ruff check .
uv run mypy app tests
uv run pytest
```

## Database

The foundation migration creates durable PostgreSQL business and audit tables for:

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
- `POST /api/v1/disputes` creates a synthetic duplicate-card case with `Idempotency-Key`.
- Repeating the same request and key returns the original case.
- Reusing the same key with a different payload returns an idempotency conflict.
- `GET /api/v1/disputes/{case_id}` returns status, timeline, evidence metadata, provider context, audit events, and correlation ID.

Do not add LangGraph, policy RAG, Model Gateway, LLM, HITL, recommendation, communication, or financial posting behavior during this change.
