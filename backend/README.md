# Backend

FastAPI/Pydantic Case API, controlled policy ingestion, hybrid policy
retrieval, bounded LangGraph workflow orchestration, and governed Model
Gateway classification from archived Phase 006
`openspec/changes/archive/2026-09-06-006-model-gateway-classification`.

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
- workflow runs
- workflow checkpoints

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
- `POST /api/v1/policies/retrievals` deterministically filters the active promoted corpus, runs lexical/vector retrieval, returns ranked cited policy context, or abstains with a policy-review signal.
- `POST /api/v1/policies/retrieval-evaluations` records retrieval quality, citation correctness, metadata filtering, and stale-policy exclusion threshold results for a retrieval configuration.
- `POST /api/v1/workflows` explicitly starts a bounded duplicate-card investigation workflow for an existing submitted case.
- `GET /api/v1/workflows/{workflow_id}` returns workflow status, current node, state version, checkpoint, interrupt, stage summary, errors and telemetry.
- `POST /api/v1/workflows/{workflow_id}/resume` resumes an interrupted workflow with `Idempotency-Key` and `If-Match` workflow state-version checks.

Load synthetic policy fixtures with:

```powershell
uv run python -m app.policy_fixture_loader
```

Run the Phase 004 retrieval smoke against the configured PostgreSQL database:

```powershell
uv run alembic -c alembic.ini current
uv run python -m app.policy_retrieval_smoke
```

Expected smoke output includes:

- `retrieval_status` = `retrieved`
- `selected_citations` with document ID, version, section, chunk hash, corpus version and index version
- `confidence` above the configured `minimum_confidence`
- `evaluation.passed` = `True`
- `telemetry` with correlation ID, candidate count, returned result count and retrieval config version
- `audit_event_id` for the append-only policy retrieval audit event

Run the Phase 006 classification evaluation and workflow smoke against the
configured PostgreSQL database:

```powershell
uv run alembic -c alembic.ini upgrade head
uv run python -m app.classification_eval
uv run python -m app.workflow_smoke
```

Expected smoke output includes:

- `workflow_id`, `case_id`, `state_version`, `checkpoint_seq` and `correlation_id`
- stage summaries for intake, Model Gateway classification, authoritative-context references and evidence gating
- classification `category`, `confidence`, `schema_version`, `prompt_version`, `model_route_version`, provider route reference, token usage and threshold metadata
- a controlled `WAITING_POLICY_REVIEW` interrupt when no promoted policy corpus exists, `WAITING_MANUAL_CLASSIFICATION` when classification is bypassed or below threshold, or `CONTROLLED_STOP` before recommendation/HITL/communication/finalization when policy context is available
- telemetry with workflow ID, current node, checkpoint count, interrupt count, classification route metadata and status

Manual Swagger UI validation:

1. Start the API with `uv run uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/docs`.
3. Use `POST /api/v1/policies/ingestions` with `X-Policy-Admin: true` to ingest an approved duplicate-card policy.
4. Use `POST /api/v1/policies/promotions` to promote the returned ingestion run.
5. Use `POST /api/v1/policies/retrievals` with effective date `2026-09-04T00:00:00Z`, product `card`, channel `web`, jurisdiction `US`, and a duplicate-card query.
6. Confirm the response contains ranked results, lexical/vector/fused scores, complete citations, corpus/index versions, retrieval config version, correlation ID and no policy-review requirement.
7. Repeat retrieval with unmatched metadata or very high `minimum_confidence` and confirm it abstains with `requires_policy_review: true`.
8. Use `POST /api/v1/policies/retrieval-evaluations` and confirm passing and failing configurations record structured threshold results.

Phase 006 adds governed Model Gateway classification only. Do not add
recommendation, communication, durable human-review task lifecycle, direct
model-provider calls from business/workflow code, or financial posting behavior
during this change.
