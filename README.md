# DisputeIQ

DisputeIQ is a production-style banking transaction dispute investigation and resolution pilot built with synthetic banking data. Phase 005 adds bounded LangGraph state and workflow orchestration so submitted duplicate-card cases can be explicitly started, checkpointed, interrupted, resumed, audited, and correlated while authoritative facts, policy controls, human decisions, communications, and financial posting remain outside autonomous workflow authority.

## Source of Truth

Use this hierarchy when requirements disagree:

1. `docs/source-of-truth/DisputeIQ_FRD_v3.1.docx`
2. Approved artifacts in `docs/architecture/`
3. Long-lived specifications in `openspec/specs/`
4. The active change in `openspec/changes/<change-id>/`
5. Code and tests

Stop and reconcile a conflict before implementing the lower-level source.

## Current Phase 005 Scope

Phase 005 includes the Phase 002 Case API baseline, Phase 003 controlled policy ingestion, Phase 004 controlled hybrid policy retrieval, and the first bounded LangGraph workflow slice.

## Recent Changes

Latest archived change: `005-langgraph-state-workflow`.

Recent capability additions:

- Phase 004 added controlled hybrid policy retrieval over approved active corpora, combining deterministic applicability filters, PostgreSQL FTS, pgvector similarity, fused scoring, confidence/ambiguity thresholds, citations, audit, and retrieval evaluation.
- Phase 005 added bounded LangGraph orchestration for submitted duplicate-card cases with durable PostgreSQL workflow runs/checkpoints, compact state, idempotent start/resume APIs, optimistic workflow state-version checks, audit-visible workflow events, and telemetry.
- Phase 005 intentionally stops before recommendation generation, durable HITL assignment, customer communication, finalization, and financial posting.

Latest local validation snapshot:

- Backend quality checks passed: `uv run ruff check .`, `uv run mypy app tests`, and `uv run pytest` with `63 passed`.
- Live PostgreSQL migration reached `20260905_0005 (head)`.
- Workflow smoke passed through submitted case creation, workflow start, intake, deterministic classification, authoritative-context references, evidence gate, policy retrieval, and controlled Phase 005 stop.
- OpenSpec long-lived specs passed with `18 passed, 0 failed` after archiving Phase 005.
- `validate --all --strict` still reports `18 passed, 1 failed` because the separate active `normalize-rfc2119-requirements` change has stale `policy-rag` MODIFIED deltas.

Case API support:

- canonical `POST/GET /api/v1/cases`, deterministic listing/search, and a case timeline endpoint
- evidence metadata registration/listing with idempotency and optimistic locking
- durable cases, idempotency records, timeline entries, evidence metadata, provider lineage, and append-only audit events
- read-only synthetic customer, account, transaction, merchant, settlement, and refund providers
- Pydantic validation, structured errors, correlation IDs, replay diagnostics, and state versions
- deprecated `/api/v1/disputes` compatibility routes backed by the same Case Service
- a React/TypeScript manual validation UI using the canonical Case API

Controlled policy ingestion support:

- protected admin policy ingestion endpoints under `/api/v1/policies`
- deterministic validation for approved/active policy status, source identity, checksums, effective dates, applicability metadata, and duplicate document versions
- durable policy documents, chunks, ingestion runs, corpus versions, evaluation results, and policy audit events
- deterministic chunk IDs, chunk hashes, section lineage, source checksums, parser/chunking configuration, embedding configuration, and correlation IDs
- pgvector and PostgreSQL lexical-search migration DDL for production-style vector and FTS readiness
- evaluation-gated promotion that preserves the last active corpus when validation, indexing, audit, or mandatory thresholds fail
- synthetic fixture loader through `uv run python -m app.policy_fixture_loader`

Hybrid policy retrieval support:

- protected read-only retrieval endpoints under `/api/v1/policies`
- deterministic eligibility filtering before retrieval by active corpus, policy status, effective date, product, channel, jurisdiction, and readiness metadata
- PostgreSQL full-text search scoring through generated `search_tsvector` plus `websearch_to_tsquery`/`ts_rank_cd`
- pgvector similarity scoring through stored vector embeddings and cosine-distance ordering
- deterministic lexical/vector score fusion with versioned retrieval configuration, top-k, confidence threshold, ambiguity threshold, citation requirement, and reranker mode
- ranked policy context with document ID, version, section, chunk ID, chunk hash, ingestion run ID, corpus version, index version, scores, correlation ID, and telemetry
- abstention and `requires_policy_review` responses for missing active corpus, no eligible candidates, low confidence, ambiguous results, or incomplete citation lineage
- append-only policy retrieval audit events for success and abstention
- retrieval regression evaluation for quality, citation correctness, metadata filtering, and stale-policy exclusion
- synthetic retrieval smoke through `uv run python -m app.policy_retrieval_smoke`

LangGraph workflow support:

- explicit workflow start/detail/resume endpoints under `/api/v1/workflows`
- durable PostgreSQL `workflow_runs` and `workflow_checkpoints` separate from case business state, policy knowledge, Redis, and audit
- compact workflow state with case ID, workflow ID, graph version, state version, correlation ID, stage summaries, side-effect keys, interrupt metadata, errors, and telemetry
- bounded graph stages for intake, deterministic duplicate-card classification routing, authoritative-context reference capture, evidence gating, policy-context resolution, and controlled Phase 005 stop
- safe idempotent start/resume behavior with optimistic `If-Match` workflow state-version checks
- workflow audit-visible events and telemetry for starts, checkpoints, interrupts, resumes, current node, checkpoint sequence, state version, graph version, and correlation ID
- synthetic workflow smoke through `uv run python -m app.workflow_smoke`

This change does not generate recommendations, persist durable HITL tasks, send communications, call model providers directly, or expose refund, credit, debit, chargeback, or financial-posting operations.

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

The Phase 005 head revision is `20260905_0005`.

Phase 005 adds workflow run and checkpoint tables over the Phase 004 runtime. The
live retrieval path still depends on the Phase 003 pgvector
`policy_chunks.embedding_vector` column and generated `search_tsvector` column.

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

Expected application tables include `audit_events`, `cases`, `evidence_metadata`,
`idempotency_records`, `provider_context`, `timeline_entries`,
`policy_ingestion_runs`, `policy_documents`, `policy_chunks`,
`policy_corpus_versions`, `policy_evaluation_results`, `policy_audit_events`,
`workflow_runs`, and `workflow_checkpoints`.

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
$runId = [guid]::NewGuid().ToString("N")
$headers = @{
  "Idempotency-Key" = "readme-case-$runId"
  "X-Correlation-ID" = "corr-readme-$runId"
}
$payload = @{
  customer_ref = "cust_1001"
  account_ref = "acct_2001"
  transaction_ref = "txn_3001"
  channel = "web"
  channel_metadata = @{ locale = "en-US"; source = "readme-smoke" }
  description = "Customer reports a duplicate card transaction at Synthetic Books."
  dispute_type = "duplicate_card_transaction"
  evidence_metadata = @(
    @{
      evidence_type = "receipt"
      file_name = "receipt.png"
      object_ref = "r2://synthetic/receipt.png"
      content_type = "image/png"
      size_bytes = 1204
      checksum_sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      source = "customer_upload"
      uploader_ref = "customer:cust_1001"
    }
  )
}
$body = $payload | ConvertTo-Json -Depth 5

$created = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/cases" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$created
```

Expected creation behavior:

- HTTP `201`
- status `Submitted`
- a generated `case_id`
- the supplied `corr-readme-<runId>` correlation ID
- initial state version `1`
- linked `CASE_CREATED` and inline evidence timeline/audit events
- six synthetic provider lineage records

Replay the identical request with the same key. It must return the original case rather than create another one:

```powershell
$replay = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/cases" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$replay.case_id
$created.case_id
```

Retrieve the case:

```powershell
$case = Invoke-RestMethod "$apiBase/api/v1/cases/$($created.case_id)"
$case | ConvertTo-Json -Depth 8
```

Search and inspect the dedicated timeline/evidence projections:

~~~powershell
$cases = Invoke-RestMethod "$apiBase/api/v1/cases?status=Submitted&customer_ref=cust_1001"
$timeline = Invoke-RestMethod "$apiBase/api/v1/cases/$($created.case_id)/timeline"
$evidence = Invoke-RestMethod "$apiBase/api/v1/cases/$($created.case_id)/evidence"
$cases.total
$timeline.items
$evidence.items
~~~

Register additional evidence metadata using the current case version:

~~~powershell
$evidenceHeaders = @{
  "Idempotency-Key" = "readme-evidence-$runId"
  "If-Match" = '"' + $case.state_version + '"'
  "X-Correlation-ID" = "corr-readme-evidence-$runId"
}
$evidenceBody = @{
  evidence_type = "customer_statement"
  file_name = "statement.pdf"
  object_ref = "r2://synthetic/statement.pdf"
  content_type = "application/pdf"
  size_bytes = 4096
  checksum_sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  source = "customer_upload"
  uploader_ref = "customer:cust_1001"
} | ConvertTo-Json
$registered = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/cases/$($created.case_id)/evidence" `
  -Headers $evidenceHeaders `
  -ContentType "application/json" `
  -Body $evidenceBody
$registered
~~~

The integration suite covers missing fields and idempotency keys, unsupported dispute
types and filters, conflicting replays, stale If-Match versions, unknown cases, provider
lineage, audit rollback, and the no-LangGraph/no-LLM architecture boundary.

## Controlled Policy Ingestion Smoke Test

Keep the backend running on port `8001`. From a new PowerShell terminal:

```powershell
$apiBase = "http://127.0.0.1:8001"
$runId = [guid]::NewGuid().ToString("N")
$policyHeaders = @{
  "X-Policy-Admin" = "true"
  "X-Correlation-ID" = "corr-policy-$runId"
}
$policyPayload = @{
  actor_ref = "policy-admin:readme"
  parser_version = "parser-v1"
  chunking_config_hash = "chunking-v1"
  embedding_model = "deterministic-test-embedding-v1"
  embedding_config_hash = "embedding-v1"
  retrieval_index_config_hash = "retrieval-v1"
  documents = @(
    @{
      document_id = "POL-DUP-CARD-$runId"
      version = "2026.09"
      title = "Synthetic duplicate-card dispute policy"
      status = "approved"
      approval_ref = "approval:readme-2026-09"
      source_identity = "synthetic-policy-manual"
      source_checksum_sha256 = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      effective_from = "2026-01-01T00:00:00Z"
      effective_to = $null
      product = "card"
      channel = "web"
      jurisdiction = "US"
      source_type = "approved_policy"
      sections = @(
        @{ section = "7.5.1"; text = "Duplicate card disputes require issuer review." },
        @{ section = "7.5.2"; text = "Policy claims require document version citations." }
      )
    }
  )
} | ConvertTo-Json -Depth 8

$run = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/policies/ingestions" `
  -Headers $policyHeaders `
  -ContentType "application/json" `
  -Body $policyPayload
$run
```

Expected ingestion behavior:

- HTTP `201`
- status `indexed`
- one document and two chunks
- each chunk has document ID, version, section, checksum, chunk hash, run ID, and both vector and lexical readiness flags
- a `POLICY_INGESTION_ACCEPTED` audit event with the supplied correlation ID

Promote the candidate corpus:

```powershell
$promotionBody = @{
  ingestion_run_id = $run.run_id
  actor_ref = "policy-admin:readme"
  corpus_version = "readme-corpus-$runId"
  index_version = "readme-index-$runId"
} | ConvertTo-Json

$promotion = Invoke-RestMethod `
  -Method Post `
  -Uri "$apiBase/api/v1/policies/promotions" `
  -Headers $policyHeaders `
  -ContentType "application/json" `
  -Body $promotionBody
$promotion
```

Expected promotion behavior:

- `promoted` is `true`
- the active corpus is the requested corpus version
- evaluation metrics include retrieval quality, citation correctness, metadata integrity, and stale-policy exclusion

Inspect chunk lineage without reading the source file:

```powershell
$chunkId = $run.documents[0].chunks[0].chunk_id
$lineage = Invoke-RestMethod `
  -Uri "$apiBase/api/v1/policies/chunks/$chunkId/lineage" `
  -Headers $policyHeaders
$lineage
```

Expected lineage fields include document ID, version, section, effective date range, ingestion run ID, checksum, chunk hash, corpus version, index version, and correlation ID.

Load and promote the checked-in synthetic fixture through the same service path:

```powershell
Set-Location backend
$env:DATABASE_URL = "postgresql+psycopg://disputeiq:disputeiq@127.0.0.1:5433/disputeiq"
uv run python -m app.policy_fixture_loader
Remove-Item Env:DATABASE_URL
Set-Location ..
```

## Hybrid Policy Retrieval Smoke Test

Keep the backend running on port `8001` and promote a policy corpus first. You can use
the ingestion smoke above, or run the checked-in Phase 004 smoke directly against the
configured PostgreSQL database:

```powershell
Set-Location backend
$env:DATABASE_URL = "postgresql+psycopg://disputeiq:disputeiq@127.0.0.1:5433/disputeiq"
uv run python -m app.policy_retrieval_smoke
Remove-Item Env:DATABASE_URL
Set-Location ..
```

Expected smoke output:

- `retrieval_status` is `retrieved`
- `selected_citations` contains document ID, version, section, chunk ID, chunk hash, ingestion run ID, corpus version, and index version
- `confidence` is above the configured `minimum_confidence`
- `evaluation.passed` is `True`
- `telemetry` includes correlation ID, eligible candidate count, returned result count, corpus/index versions, retrieval config version, and latency
- `audit_event_id` identifies the append-only policy retrieval audit event
- stale and wrong-product fixtures are listed as excluded fixture IDs

Manual retrieval API validation from Swagger UI:

1. Open `http://127.0.0.1:8001/docs`.
2. Use `POST /api/v1/policies/ingestions` with `X-Policy-Admin: true` to ingest an approved duplicate-card policy.
3. Use `POST /api/v1/policies/promotions` to promote the returned ingestion run.
4. Use `POST /api/v1/policies/retrievals` with effective date `2026-09-04T00:00:00Z`, product `card`, channel `web`, jurisdiction `US`, and a duplicate-card query.
5. Confirm the response includes ranked results, lexical/vector/fused scores, complete citations, corpus/index versions, retrieval config version, correlation ID, telemetry, and `requires_policy_review: false`.
6. Repeat retrieval with unmatched product/channel/jurisdiction or a very high `minimum_confidence` and confirm the response abstains with `requires_policy_review: true`.
7. Use `POST /api/v1/policies/retrieval-evaluations` and confirm passing and failing retrieval configurations record structured threshold results.

## LangGraph Workflow Smoke Test

Keep PostgreSQL running and apply the latest migration first:

```powershell
Set-Location backend
$env:DATABASE_URL = "postgresql+psycopg://disputeiq:disputeiq@127.0.0.1:5433/disputeiq"
uv run alembic -c alembic.ini upgrade head
uv run python -m app.workflow_smoke
Remove-Item Env:DATABASE_URL
Set-Location ..
```

Expected smoke output:

- `status` is `CONTROLLED_STOP` when an applicable promoted policy corpus exists, or `WAITING_POLICY_REVIEW` when no active corpus is available
- `workflow_id`, `case_id`, `state_version`, `checkpoint_seq`, and `correlation_id` are present
- `stage_summaries` includes intake, deterministic classification, authoritative-context references, evidence gating, and policy context when available
- `interrupt` records the controlled Phase 005 stop or review requirement
- `telemetry` includes workflow ID, current node, checkpoint count, interrupt count, status, graph version, state version, and correlation ID

Manual workflow API validation from Swagger UI:

1. Open `http://127.0.0.1:8001/docs`.
2. Create or reuse a submitted duplicate-card case from `POST /api/v1/cases`.
3. Use `POST /api/v1/workflows` with `Idempotency-Key` and the case ID.
4. Confirm the response includes workflow ID, status, current node, state version, graph version, latest checkpoint, interrupt metadata, stage summaries, telemetry, and correlation ID.
5. Repeat the same start request with the same idempotency key and payload; confirm the original workflow response is replayed.
6. Use `GET /api/v1/workflows/{workflow_id}` and confirm the persisted checkpoint and stage summaries are returned.
7. Use `POST /api/v1/workflows/{workflow_id}/resume` with stale `If-Match`; confirm a structured conflict response and no state mutation.

## Validate the Project

### Backend

From `backend/`:

```powershell
uv sync
uv run ruff check .
uv run mypy app tests
uv run pytest
```

Expected result: Ruff passes, mypy reports no issues, and pytest reports `63 passed`.

Focused backend checks:

```powershell
uv run pytest tests/unit/test_schemas.py
uv run pytest tests/unit/test_case_service.py
uv run pytest tests/unit/test_synthetic_providers.py
uv run pytest tests/integration/test_api.py
uv run pytest tests/integration/test_architecture_boundaries.py
uv run pytest tests/integration/test_policy_ingestion_api.py
uv run pytest tests/integration/test_workflow_api.py
uv run pytest tests/unit/test_policy_ingestion_service.py
uv run pytest tests/unit/test_policy_retrieval_service.py
uv run pytest tests/unit/test_workflow_graph.py
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

Expected result: TypeScript checks pass, Vitest reports `4 passed`, the Vite production
build succeeds, and npm reports zero high-severity vulnerabilities.

## Validate Phase 002 in the UI

Use both browser surfaces. The React UI covers the analyst-facing create/replay/retrieve
path. Swagger UI covers the complete API surface, including search, evidence registration,
optimistic locking, and structured error responses.

### React UI Validation

Open `http://127.0.0.1:5173` while the backend is running on port `8001`.

1. Confirm the duplicate-card form loads the synthetic customer, account, and transaction
   references.
2. Enter a unique idempotency key and optional correlation ID, then select
   **Create synthetic case**.
3. Confirm the response shows a generated case ID, `Submitted` status, correlation ID,
   timeline, evidence metadata, provider context, and audit events.
4. Confirm provider context includes customer, account, transaction, merchant, settlement,
   and refund records with source lineage.
5. Submit the unchanged form again with the same idempotency key. The same case ID must be
   returned without a duplicate `CASE_CREATED` event.
6. Change the description but retain the same idempotency key. The UI must display the
   idempotency-conflict error and no second case may be created.
7. Paste the case ID into the lookup control and select **Load case**. The same persisted
   aggregate must be displayed.
8. Clear the transaction reference and submit. Local required-field validation must block
   the request.
9. Stop the backend temporarily and submit again. The UI must display a visible request
   failure rather than silently ignoring it.

### Swagger UI Validation

Open `http://127.0.0.1:8001/docs`. The canonical `cases` group must expose:

- `POST /api/v1/cases`
- `GET /api/v1/cases`
- `GET /api/v1/cases/{case_id}`
- `POST /api/v1/cases/{case_id}/evidence`
- `GET /api/v1/cases/{case_id}/evidence`
- `GET /api/v1/cases/{case_id}/timeline`

The `policies` group must expose protected ingestion, promotion, retrieval, evaluation,
and lineage routes under `/api/v1/policies`.

The `workflows` group must expose:

- `POST /api/v1/workflows`
- `GET /api/v1/workflows/{workflow_id}`
- `POST /api/v1/workflows/{workflow_id}/resume`

The `/api/v1/disputes` create/retrieve routes remain visible only as deprecated
compatibility delegates.

Create a case through `POST /api/v1/cases` using a unique `Idempotency-Key`, a
correlation ID, and the synthetic references shown in the API smoke payload. Copy the
returned `case_id` and confirm the initial `state_version` is `1`.

Then validate:

1. Use `GET /api/v1/cases` with `status=Submitted`, `customer_ref=cust_1001`,
   `transaction_ref=txn_3001`, or `channel=web`. Matching summaries must be returned
   in deterministic order.
2. Register evidence through `POST /api/v1/cases/{case_id}/evidence` with a unique
   idempotency key and `If-Match` entered as `"1"`. The case version must advance to
   `2`.
3. Replay the identical evidence request with the same key. The response must report
   `replayed: true` and return the same evidence ID.
4. Submit another evidence request with a new key but stale `If-Match: "1"`. Expect
   HTTP `409` with `OPTIMISTIC_LOCK_CONFLICT` and no additional evidence record.
5. Use the evidence and timeline GET endpoints. Confirm chronological
   `CASE_CREATED` and `EVIDENCE_METADATA_REGISTERED` entries with linked audit IDs.
6. Retrieve the case again and confirm version `2`, evidence lineage, six provider
   records, replay diagnostics, and one material audit event for each accepted mutation.
7. Omit `Idempotency-Key`, submit an unsupported dispute type, request an unknown case,
   and reuse a key with a changed payload. Confirm stable error codes and correlation IDs.

## Phase 002 Validation Evidence

The completed OpenSpec changes are archived at:

- `openspec/changes/archive/2026-08-30-001-platform-foundation`
- `openspec/changes/archive/2026-08-30-002-case-api-persistence`

Phase 002 finished with all 34 tasks complete. Its task evidence remains traceable in
`openspec/changes/archive/2026-08-30-002-case-api-persistence/tasks.md` and
`docs/implementation/phase-002-case-api-gap-review.md`.

| Task group | Primary validation |
| --- | --- |
| 1. Gap review | Review `docs/implementation/phase-002-case-api-gap-review.md` and OpenAPI |
| 2. Case persistence | Alembic revision/table checks against Compose PostgreSQL, then service/schema tests |
| 3. Case API | `uv run pytest tests/integration/test_api.py` |
| 4. Evidence metadata | API, service, and failure-contract tests |
| 5. Timeline and audit | Service, API, and audit rollback tests |
| 6. Provider contracts | `uv run pytest tests/unit/test_synthetic_providers.py` |
| 7. Architecture boundaries | `uv run pytest tests/integration/test_architecture_boundaries.py` |
| 8. CI, docs, final validation | All backend/frontend checks, PostgreSQL migration verification, API smoke, dependency audit, and strict main-spec validation |

## Phase 003 Validation Evidence

The completed OpenSpec change is archived at
`openspec/changes/archive/2026-09-03-003-controlled-policy-ingestion`.
Its approved deltas are synced into the long-lived specs under `openspec/specs/`.

| Task group | Primary validation |
| --- | --- |
| 1. Gap review | OpenSpec proposal/design plus migration and boundary tests |
| 2. Policy persistence | Alembic revision/table/index checks and repository/service tests |
| 3. Validation/chunking | `uv run pytest tests/unit/test_policy_ingestion_service.py` |
| 4. Embedding/indexing/promotion | Service and API promotion tests, migration pgvector/FTS contract test |
| 5. Admin API/fixture loader | `uv run pytest tests/integration/test_policy_ingestion_api.py` |
| 6. Audit/security/observability | Policy API tests, audit service tests, architecture-boundary tests |
| 7. Evaluation/docs/final validation | Backend checks, policy smoke, OpenSpec strict validation |

Latest validation snapshot:

- `uv run ruff check .`: passed
- `uv run mypy app tests`: passed with no issues in 32 source files
- `uv run pytest`: `41 passed`
- `uv run python -m app.policy_ingestion_smoke`: passed through `validated -> chunked -> embedded -> indexed -> evaluated -> promoted -> audited`
- `uv run alembic -c alembic.ini upgrade head`: upgraded Compose PostgreSQL to `20260903_0003`
- PostgreSQL verification confirmed `vector`, policy tables, lexical GIN indexing, and vector cosine indexing
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`: `18 passed, 0 failed` at Phase 003 archive time

## Phase 004 Validation Evidence

The completed OpenSpec change is archived at
`openspec/changes/archive/2026-09-04-004-hybrid-policy-retrieval`.
Its approved deltas are synced into the long-lived specs under `openspec/specs/`.

| Task group | Primary validation |
| --- | --- |
| 1. Gap review | `docs/implementation/phase-004-hybrid-policy-retrieval-gap-review.md` |
| 2. Retrieval contracts/configuration | Schema, API, and service tests |
| 3. Eligibility and database retrieval | PostgreSQL FTS/pgvector SQL guard, service tests, live smoke |
| 4. Citations/confidence/audit | `uv run pytest tests/unit/test_policy_retrieval_service.py` |
| 5. API/smoke/evaluation | `uv run pytest tests/integration/test_policy_ingestion_api.py` and `uv run python -m app.policy_retrieval_smoke` |
| 6. Documentation/final validation | Backend checks, long-lived spec validation, and archived task checklist |

Latest validation snapshot:

- `uv run ruff check .`: passed
- `uv run mypy app tests`: passed with no issues in 35 source files
- `uv run pytest`: `52 passed`
- `uv run alembic -c alembic.ini current`: `20260903_0003 (head)`
- `uv run python -m app.policy_retrieval_smoke`: passed through `promoted corpus -> deterministic eligibility -> PostgreSQL lexical search -> pgvector similarity -> fusion/rerank -> cited context -> confidence/audit/evaluation`
- Smoke output included `retrieval_status: retrieved`, confidence `0.541734`, selected citations, telemetry, audit event ID, and `evaluation.passed: True`
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`: `17 passed, 0 failed`
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`: `17 passed, 1 failed` because of the pre-existing active `normalize-rfc2119-requirements` change

## Phase 005 Validation Evidence

The completed OpenSpec change is archived at
`openspec/changes/archive/2026-09-05-005-langgraph-state-workflow`.
Its approved deltas are synced into the long-lived specs under `openspec/specs/`.

| Task group | Primary validation |
| --- | --- |
| 1. Gap review | `docs/implementation/phase-005-langgraph-state-workflow-gap-review.md` |
| 2. Workflow persistence | Alembic revision/table/index checks, repository tests, and migration contract tests |
| 3. State contract | Workflow schema tests and compact checkpoint-state validation |
| 4. Graph construction | `uv run pytest tests/unit/test_workflow_graph.py` |
| 5. Workflow service/API | `uv run pytest tests/integration/test_workflow_api.py` and `uv run python -m app.workflow_smoke` |
| 6. Boundaries/docs/final validation | Architecture-boundary tests, backend checks, OpenSpec archive, and long-lived spec validation |

Latest validation snapshot:

- `uv sync`: passed
- `uv run ruff check .`: passed
- `uv run mypy app tests`: passed with no issues in 41 source files
- `uv run pytest`: `63 passed`
- `uv run alembic -c alembic.ini current`: `20260905_0005 (head)`
- `uv run python -m app.workflow_smoke`: passed through submitted case creation, workflow start, intake, deterministic classification, authoritative-context references, evidence gate, policy retrieval and controlled Phase 005 stop
- Smoke output included `status: CONTROLLED_STOP`, `current_node: controlled_stop`, `state_version: 3`, `checkpoint_seq: 2`, six authoritative-context references, retrieved policy context, correlation ID and workflow telemetry
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict`: `18 passed, 0 failed`
- `npx.cmd -y @fission-ai/openspec@1.10.0 validate --all --strict`: `18 passed, 1 failed` because of the separate active `normalize-rfc2119-requirements` change

## OpenSpec Status and Commands

The commands below use the approved pinned CLI on Windows. If a compatible global
`openspec` command is available, it can replace the full
`npx.cmd -y @fission-ai/openspec@1.10.0` prefix.

From the repository root, inspect active changes and validate the long-lived specs:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 list --json
npx.cmd -y @fission-ai/openspec@1.10.0 validate --specs --strict
```

Expected result:

- Phase 001, Phase 002, Phase 003, Phase 004, and Phase 005 are absent from the active-change list because they are archived.
- `normalize-rfc2119-requirements` is the only active change and its checklist is complete.
- Strict long-lived-spec validation reports `18 passed, 0 failed`.

`validate --all --strict` also validates every active change. In the latest Phase 005
snapshot it reports `18 passed, 1 failed` because `normalize-rfc2119-requirements`
is still an active stale normalization change after newer specs were synced.
That active change currently omits newer `policy-rag` scenarios from its MODIFIED
requirements, including no-applicable-policy candidates, hybrid lexical/vector
retrieval, stale-policy exclusion, citation lineage, missing active corpus, and
missing-citation continuation gates.

Inspect the archived artifacts and completed Phase 002/Phase 003/Phase 004/Phase 005 checklists with:

```powershell
Get-ChildItem openspec/changes/archive/2026-08-30-001-platform-foundation
Get-ChildItem openspec/changes/archive/2026-08-30-002-case-api-persistence
Get-ChildItem openspec/changes/archive/2026-09-03-003-controlled-policy-ingestion
Get-ChildItem openspec/changes/archive/2026-09-04-004-hybrid-policy-retrieval
Get-ChildItem openspec/changes/archive/2026-09-05-005-langgraph-state-workflow
rg -n "^- \[x\]" openspec/changes/archive/2026-08-30-002-case-api-persistence/tasks.md
rg -n "^- \[x\]" openspec/changes/archive/2026-09-03-003-controlled-policy-ingestion/tasks.md
rg -n "^- \[x\]" openspec/changes/archive/2026-09-04-004-hybrid-policy-retrieval/tasks.md
rg -n "^- \[x\]" openspec/changes/archive/2026-09-05-005-langgraph-state-workflow/tasks.md
```

### Start a Future Change

For each later sprint or independently reviewable capability:

```powershell
npx.cmd -y @fission-ai/openspec@1.10.0 new change "<change-id>"
npx.cmd -y @fission-ai/openspec@1.10.0 status --change "<change-id>" --json
npx.cmd -y @fission-ai/openspec@1.10.0 instructions proposal --change "<change-id>" --json
```

Create and review proposal, delta specs, design, and tasks before implementation. During
implementation, validate the active change after each coherent task group. Archive only
after all tasks, focused tests, full application checks, and human review are complete.

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
