DisputeIQ Tech Stack:

Frontend: React + TypeScript
Backend/API: Python 3.12 + FastAPI + Pydantic
Workflow orchestration: LangGraph
Operational database: PostgreSQL
Workflow checkpoint store: PostgreSQL, logically separated from business state
Vector database / RAG store: pgvector on PostgreSQL
Cache / transient coordination / locks / lightweight queueing: Redis
Object/file storage: Cloudflare R2 or S3-compatible object storage
Policy RAG: approved policy ingestion, chunking, embeddings, deterministic metadata filtering, lexical + vector retrieval, reranking, citations
AI platform: central Model Gateway with provider abstraction, prompt/version management, token controls, response validation, guardrails, fallback/routing
LLM providers: provider-neutral design, with OpenAI / Azure OpenAI / Anthropic-style providers supported through the gateway
Observability: OpenTelemetry + LangSmith + LangWatch
Edge/security: Cloudflare DNS, WAF, DDoS protection, rate limiting, Zero Trust
Containerization/local runtime: Docker + Docker Compose
CI/CD: GitHub Actions
Specification-driven development: OpenSpec
AI coding workflow: VS Code + Codex
Database migrations: Alembic
Testing: Pytest for backend/unit/integration; RAG/AI evaluation suites for retrieval, citation, grounding, safety, and E2E quality