# DisputeIQ

DisputeIQ is a production-style banking transaction dispute investigation and resolution pilot built with synthetic banking data. The current `001-platform-foundation` change implements deterministic dispute intake, PostgreSQL persistence, idempotency, read-only synthetic provider context, audit events, timeline visibility, and a React foundation UI.

## Source of Truth

Use this hierarchy when requirements disagree:

1. `docs/source-of-truth/DisputeIQ_FRD_v3.0_8Week_OpenSpec_GWT_Reference_TOC_Fixed.docx`
2. Approved artifacts in `docs/architecture/`
3. Long-lived specifications in `openspec/specs/`
4. The active change in `openspec/changes/<change-id>/`
5. Code and tests

Stop and reconcile a conflict before implementing the lower-level source.

## Current Foundation Scope

The foundation supports:

- creating, safely replaying, and retrieving a synthetic duplicate-card dispute
- persisting cases, idempotency records, timeline entries, evidence metadata, provider context, and audit events in PostgreSQL
- deterministic mandatory-field validation
- accepting or generating correlation IDs
- emitting an append-only `CASE_CREATED` business audit event
- displaying case detail in a React/TypeScript UI

This change does not execute LangGraph, call an LLM or Model Gateway, use policy RAG, perform HITL decisioning, send communications, or expose refund, credit, debit, chargeback, or financial-posting operations.

## Prerequisites

- Docker Desktop with Docker Compose
- Python 3.12
- `uv`
- Node.js 22 and npm
- PowerShell on Windows

Check the tools from the repository root:

```powershell
docker --version
docker compose version
python --version
uv --version
node --version
npm.cmd --version
```

## Run the Application

Run each long-lived process in a separate PowerShell terminal.

### 1. Start PostgreSQL and Redis

From the repository root:

```powershell
docker compose up -d postgres redis
docker compose ps
docker compose exec -T postgres pg_isready -U disputeiq -d disputeiq
```

PostgreSQL is ready when `pg_isready` reports `accepting connections`.

### 2. Check and Apply the Database Migration

First check whether Alembic is already installed in the database:

```powershell
docker compose exec -T postgres psql `
  -U disputeiq `
  -d disputeiq `
  -c "SELECT to_regclass('public.alembic_version');"
```

If the result is `alembic_version`, inspect the revision and do not replay the offline migration SQL:

```powershell
docker compose exec -T postgres psql `
  -U disputeiq `
  -d disputeiq `
  -c "SELECT version_num FROM alembic_version;"
```

The foundation revision is `20260829_0001`.

If `alembic_version` does not exist, try the normal online migration from `backend/`:

```powershell
Set-Location backend
$env:DATABASE_URL = "postgresql+psycopg://disputeiq:disputeiq@127.0.0.1:5433/disputeiq"
uv run alembic -c alembic.ini upgrade head
uv run alembic -c alembic.ini current
Remove-Item Env:DATABASE_URL
Set-Location ..
```

If host TCP authentication remains unavailable but the container login succeeds, apply the migration once through the container:

```powershell
Set-Location backend
uv run alembic -c alembic.ini upgrade head --sql |
  docker compose -f ..\docker-compose.yml exec -T postgres `
    psql -v ON_ERROR_STOP=1 -U disputeiq -d disputeiq
Set-Location ..
```

Do not run the offline SQL command again after `alembic_version` exists. Offline Alembic generation cannot inspect the database and will try to recreate existing objects.

Verify the installed revision and tables:

```powershell
docker compose exec -T postgres psql `
  -U disputeiq `
  -d disputeiq `
  -c "SELECT version_num FROM alembic_version;"

docker compose exec -T postgres psql `
  -U disputeiq `
  -d disputeiq `
  -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
```

Expected application tables are `audit_events`, `cases`, `evidence_metadata`, `idempotency_records`, `provider_context`, and `timeline_entries`.

### 3. Start the Backend

From `backend/`:

```powershell
Set-Location backend
$env:DATABASE_URL = "postgresql+psycopg://disputeiq:disputeiq@127.0.0.1:5433/disputeiq"
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Keep this terminal open. Validate the running service from another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

Expected response:

```json
{"status":"ok"}
```

Useful backend URLs:

- API: `http://127.0.0.1:8001`
- OpenAPI UI: `http://127.0.0.1:8001/docs`
- OpenAPI JSON: `http://127.0.0.1:8001/openapi.json`

Remove the terminal-scoped database setting after stopping the backend:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
```

### 4. Start the Frontend

From `frontend/`:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

The Vite development server proxies `/api` requests to the FastAPI backend at `http://127.0.0.1:8001`. Keep the backend running before creating or looking up a case. Request failures are shown in the UI instead of being silently ignored.

## API Smoke Test

Keep the backend running on port `8001`. From a new PowerShell terminal:

```powershell
$apiBase = "http://127.0.0.1:8001"
$headers = @{
  "Idempotency-Key" = "readme-demo-001"
  "X-Correlation-ID" = "corr-readme-001"
}
$payload = @{
  customer_ref = "cust_1001"
  account_ref = "acct_2001"
  transaction_ref = "txn_3001"
  channel = "web"
  description = "Customer reports a duplicate card transaction at Synthetic Books."
  dispute_type = "duplicate_card_transaction"
  evidence_metadata = @(
    @{
      file_name = "receipt.png"
      content_type = "image/png"
      size_bytes = 1204
      checksum_sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      uploader_ref = "customer:cust_1001"
    }
  )
}
$body = $payload | ConvertTo-Json -Depth 5

$created = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/disputes" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$created
```

Expected creation behavior:

- HTTP `201`
- status `Submitted`
- a generated `case_id`
- correlation ID `corr-readme-001`
- one `CASE_CREATED` timeline event
- one `CASE_CREATED` audit event
- synthetic provider context

Replay the identical request with the same key. It must return the original case rather than create another one:

```powershell
$replay = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/disputes" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$replay.case_id
$created.case_id
```

Retrieve the case:

```powershell
$case = Invoke-RestMethod "$apiBase/api/v1/disputes/$($created.case_id)"
$case | ConvertTo-Json -Depth 8
```

For validation and idempotency-conflict scenarios, run the backend integration tests described below. They assert HTTP `422` for missing mandatory fields and HTTP `409` when an idempotency key is reused with a different payload.

## Validate the Project

### Backend

From `backend/`:

```powershell
uv sync
uv run ruff check .
uv run mypy app tests
uv run pytest
```

Focused backend checks:

```powershell
uv run pytest tests/unit/test_schemas.py
uv run pytest tests/unit/test_case_service.py
uv run pytest tests/unit/test_synthetic_providers.py
uv run pytest tests/integration/test_api.py
uv run pytest tests/integration/test_architecture_boundaries.py
```

### Frontend

From `frontend/`:

```powershell
npm.cmd ci
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
npm.cmd audit --audit-level=high
```

### Manual UI Checklist

With the frontend running, verify:

- the duplicate-card intake form renders with the synthetic fixture defaults
- required fields show local validation feedback
- idempotency key and correlation ID controls are visible
- clicking **Create synthetic case** creates a case and renders `Submitted`, timeline, evidence metadata, provider context, audit events, and correlation ID
- reusing the same idempotency key and unchanged payload returns the same case ID
- entering the created case ID and clicking **Load case** retrieves the same case
- stopping the backend and submitting again shows a visible request error

## Validation by OpenSpec Task Group

Use the following checks while completing `openspec/changes/001-platform-foundation/tasks.md`:

| Task group | Primary validation |
| --- | --- |
| 1. Backend foundation | `uv run ruff check .`, `uv run mypy app tests`, `uv run pytest tests/unit/test_schemas.py tests/integration/test_api.py` |
| 2. Persistence and migration | Alembic revision/table checks against Compose PostgreSQL, then `uv run pytest tests/unit/test_case_service.py` |
| 3. Intake and idempotency | `uv run pytest tests/integration/test_api.py` |
| 4. Synthetic provider context | `uv run pytest tests/unit/test_synthetic_providers.py tests/unit/test_case_service.py` |
| 5. Audit, timeline, correlation | `uv run pytest tests/unit/test_case_service.py tests/integration/test_api.py` |
| 6. Frontend foundation UI | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build` |
| 7. Architecture boundaries | `uv run pytest tests/integration/test_architecture_boundaries.py` |
| 8. CI, docs, final validation | all backend/frontend checks, PostgreSQL migration verification, API smoke, dependency audit, and strict OpenSpec validation |

Do not mark an OpenSpec task complete until its behavior and named validation have passed.

## OpenSpec Command Sequence

OpenSpec does not execute an individual checklist task. It reports the active change context and progress; implementation and tests are performed in the repository, and the matching checkbox in `tasks.md` is changed from `[ ]` to `[x]` only after verification.

The commands below use the approved pinned CLI on Windows. If a compatible global `openspec` command is available, it can replace the full `npx.cmd -y @fission-ai/openspec@1.10.0` prefix.

### Inspect the Active Change

From the repository root:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 list --json
npx.cmd -y @fission-ai/openspec@1.10.0 status --change "001-platform-foundation" --json
npx.cmd -y @fission-ai/openspec@1.10.0 show "001-platform-foundation" --type change
npx.cmd -y @fission-ai/openspec@1.10.0 instructions apply --change "001-platform-foundation" --json
```

### Repeat for Each Pending Task

1. Read the proposal, design, delta specs, and next unchecked task returned by `instructions apply`.
2. Identify the governing FRD requirement and long-lived capability specification.
3. Implement only that task and add or update its tests.
4. Run the focused validation from the task-group table.
5. Mark only the verified task `[x]` in `openspec/changes/001-platform-foundation/tasks.md`.
6. Validate the change and refresh progress:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 validate "001-platform-foundation" --type change --strict
npx.cmd -y @fission-ai/openspec@1.10.0 instructions apply --change "001-platform-foundation" --json
```

Repeat until the apply instructions report `state: "all_done"` and no unchecked tasks remain.

### Final Validation and Archive

After all task-level checks and the full application smoke test pass:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 validate "001-platform-foundation" --type change --strict
npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict
npx.cmd -y @fission-ai/openspec@1.10.0 instructions archive --change "001-platform-foundation" --json
```

Review the archive instructions and delta-to-main-spec updates. Archive only after human approval:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 archive "001-platform-foundation" --yes
npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict
npx.cmd -y @fission-ai/openspec@1.10.0 list --json
```

Do not archive while tasks remain incomplete or required validation is failing.

### Start a Future Change

For each later sprint or independently reviewable capability:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 new change "<change-id>"
npx.cmd -y @fission-ai/openspec@1.10.0 status --change "<change-id>" --json
npx.cmd -y @fission-ai/openspec@1.10.0 instructions proposal --change "<change-id>" --json
```

Create and review proposal, delta specs, design, and tasks before implementation. Then use the same per-task apply, validation, and archive sequence described above.

## Troubleshooting

### Alembic reports no `script_location`

Run Alembic from `backend/` and explicitly load the checked-in configuration:

```powershell
Set-Location backend
uv run alembic -c alembic.ini upgrade head
```

### Host PostgreSQL rejects the Compose password

Confirm the intended service is running and the in-container login works:

```powershell
docker compose up -d postgres
docker compose exec -T postgres pg_isready -U disputeiq -d disputeiq
docker compose exec -T postgres psql -U disputeiq -d disputeiq -c "SELECT current_user, current_database();"
```

An existing Docker volume can retain an older database-role password because `POSTGRES_PASSWORD` applies only during first initialization. For a local development database, align the role with the checked-in Compose credential, then retry the normal online migration or backend connection:

```powershell
docker compose exec -T postgres psql `
  -U disputeiq `
  -d disputeiq `
  -c "ALTER ROLE disputeiq WITH PASSWORD 'disputeiq';"
```

DisputeIQ maps PostgreSQL to host port `5433` by default to avoid the common native PostgreSQL port `5432`. Override it with `POSTGRES_HOST_PORT` only when the selected host port is known to be free, and keep `DATABASE_URL` aligned with that value.

### Offline migration reports `alembic_version` already exists

The migration has already been applied. Do not rerun static SQL. Verify the revision instead:

```powershell
docker compose exec -T postgres psql `
  -U disputeiq `
  -d disputeiq `
  -c "SELECT version_num FROM alembic_version;"
```

### PostgreSQL reports a collation-version mismatch

The warning does not prevent this foundation migration. Do not delete the Docker volume solely to silence it. Plan a reviewed local database maintenance or rebuild if collation-sensitive indexes are introduced or the warning must be removed.

### PowerShell blocks `npm.ps1`

Use `npm.cmd` and `npx.cmd`, as shown throughout this runbook.

## Stop Local Services

Stop the Compose services without deleting their persisted volume:

```powershell
docker compose stop postgres redis
```

Do not run `docker compose down -v` unless the local database is explicitly disposable; `-v` removes the persisted PostgreSQL data.
