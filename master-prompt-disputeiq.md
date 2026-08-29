# ROLE

Act as a Principal AI Systems Architect, Principal Software Engineer,
AI Platform Architect, Technical Program Lead, and OpenSpec-driven
development mentor.

You are helping me plan the implementation of:

DisputeIQ — AI-Powered Banking Transaction Dispute Investigation
& Resolution Platform.

This is my INITIAL production-style pilot project.

I want this project not merely to demonstrate a use case, but to give me
hands-on implementation experience across the complete modern
Generative AI / Agentic AI engineering lifecycle.

I am implementing the project myself using:

- Visual Studio Code
- Codex
- OpenSpec
- GitHub
- GitHub Actions

Target implementation duration:

PRIMARY PLAN: 10 weeks
OPTIONAL HARDENING BUFFER: Weeks 11–12

Use 2-week sprints unless a different subdivision materially improves
delivery sequencing.

Do NOT implement application code yet.

Your job in this task is to produce an implementation-ready,
sprint-based execution blueprint that I can subsequently execute
through OpenSpec changes using Codex.


# AUTHORITATIVE INPUT DOCUMENTS

Before producing the plan, inspect the repository and read completely:

1. DisputeIQ Functional Requirements / FRD v3.0
2. DisputeIQ High-Level Design / HLD v1.0
3. DisputeIQ Detailed Design / LLD v1.0
4. DisputeIQ Tech Stack
5. Any architecture/data-flow/sequence diagrams available in the repository
6. Existing OpenSpec files, ADRs, code, GitHub workflows and project
   structure if they already exist

Treat these documents as the implementation baseline.

Use this precedence when interpreting the project:

FRD
    -> defines functional behaviour, scope and acceptance expectations

HLD
    -> defines architecture boundaries and system responsibilities

LLD
    -> defines implementation contracts, state model, APIs,
       component boundaries, data structures, workflow behaviour
       and failure handling

Tech Stack
    -> defines implementation technology choices

Do NOT silently invent requirements.

Where documents disagree, create a section:

"Design Reconciliation / Decision Required"

and show:

- conflicting statements
- affected FR/HLD/LLD sections
- implementation impact
- recommended resolution
- whether an ADR is required

Clearly classify every new recommendation as:

VERIFIED REQUIREMENT
PROPOSED IMPLEMENTATION DECISION
ASSUMPTION
OPEN DECISION
POST-PILOT ENHANCEMENT


# MANDATORY ARCHITECTURAL PRINCIPLES

Preserve the architecture defined by the FRD/HLD/LLD.

1. LangGraph is a STATEFUL WORKFLOW ORCHESTRATOR.

Do NOT redesign DisputeIQ as an uncontrolled multi-agent or
agent-to-agent system.

2. Preserve the 11-stage workflow:

1  Intake & Normalize
2  Classify & Route
3  Acquire Authoritative Context
4  Assess Evidence Completeness
5  Resolve Applicable Policy
6  Execute Decision Rules
7  Case Confidence & Escalation
8  Generate Recommendation
9  Human Decision
10 Approved Communication
11 Finalize & Audit

3. Preserve clear separation between:

- deterministic processing
- bounded AI-assisted processing
- authoritative banking/tool data
- human-in-the-loop decisions

4. LLMs MUST NOT:

- make authoritative financial decisions
- execute deterministic eligibility rules
- execute mandatory evidence rules
- autonomously post refunds/credits/chargebacks
- replace human approval
- become a source of authoritative transaction facts

5. Material financial outcomes remain human governed.

6. Large evidence/document payloads must NOT be stored inside
LangGraph checkpoint state.

7. Business state, workflow checkpoint state, policy/vector state,
audit state and transient Redis state must remain logically distinct.

8. All material operations must be:

- traceable
- auditable
- versioned
- observable
- idempotent where required

9. Fail safely when:

- evidence is missing
- confidence is low
- policy retrieval is ambiguous
- deterministic rule execution fails
- model output is invalid
- dependencies are unavailable


# FIXED TECHNOLOGY BASELINE

Assume the following baseline unless an attached architecture document
explicitly supersedes it:

Frontend
- React
- TypeScript

Backend
- Python 3.12
- FastAPI
- Pydantic v2

Workflow
- LangGraph Python

Operational database
- PostgreSQL
- Alembic migrations

Workflow checkpoint store
- PostgreSQL
- logically isolated from business state

Policy / RAG
- PostgreSQL
- pgvector
- governed policy ingestion
- chunking
- embeddings
- metadata filtering
- lexical + vector hybrid retrieval
- reranking
- citations

Transient coordination
- Redis

Object storage
- Cloudflare R2 / S3-compatible storage

AI Platform
- Provider-neutral Model Gateway

Potential providers behind gateway
- OpenAI
- Azure OpenAI
- Anthropic-compatible providers

Observability
- OpenTelemetry
- LangSmith
- LangWatch

Edge / Security
- Cloudflare DNS
- WAF
- DDoS protection
- Rate limiting
- Zero Trust

Local development
- Docker
- Docker Compose

CI/CD
- GitHub Actions

Specification-driven development
- OpenSpec

Testing
- pytest
- integration tests
- LangGraph workflow tests
- deterministic rule regression
- RAG evaluation
- AI evaluation
- security testing
- resilience testing
- E2E tests


# PILOT BOUNDARY

The pilot must support the three FRD MVP dispute types:

1. Duplicate card transaction
2. Failed UPI transfer
3. ATM debit without cash

Use only:

- synthetic/mock customer data
- synthetic/mock transaction data
- synthetic/mock banking systems/providers
- sample policy documents

Do not introduce real banking connectivity into the pilot.


# IMPLEMENTATION STRATEGY

Use VERTICAL-SLICE-FIRST development.

Do NOT try to build all three dispute types simultaneously.

Preferred sequence:

1. Establish the platform foundation.
2. Implement Duplicate Card Transaction as the first complete vertical
   slice through all 11 workflow stages.
3. Stabilize:
   - LangGraph
   - persistence
   - controlled RAG
   - deterministic rules
   - HITL
   - audit
   - Model Gateway
   - observability
4. Expand the same platform to:
   - Failed UPI
   - ATM debit without cash
5. Harden and deploy the complete pilot.

Explain any reason for deviating from this sequence.


# OPENSPEC DELIVERY METHOD

The implementation MUST be OpenSpec-driven.

Do NOT create one giant OpenSpec change for the entire application.

Break the implementation into independently reviewable,
testable and archivable OpenSpec changes.

For EACH OpenSpec change require:

openspec/changes/<change-id>/

    proposal.md
    design.md
    tasks.md
    specs/... delta specifications

Each change must follow:

Explore
    ↓
Proposal
    ↓
Specification / GWT scenarios
    ↓
Design
    ↓
Tasks
    ↓
Human Plan Review
    ↓
Codex Implementation
    ↓
Validation
    ↓
GitHub PR / CI
    ↓
OpenSpec Sync
    ↓
Archive

Codex must implement ONLY approved tasks belonging to the
currently active OpenSpec change.

Every change must map:

FR Requirement
    ↓
OpenSpec Capability
    ↓
Change ID
    ↓
GWT Scenario
    ↓
Design
    ↓
Task
    ↓
Code
    ↓
Test / Evaluation
    ↓
CI Evidence


# PRIMARY TASK

Generate a detailed 10-week implementation plan.

Also explain how the same implementation could:

- be compressed to 8 weeks
- use Weeks 11–12 as optional hardening / Cloudflare deployment buffer


# REQUIRED OUTPUT


============================================================
PART 1 — DOCUMENT RECONCILIATION
============================================================

Summarize what the FRD, HLD, LLD and Tech Stack collectively require.

Create:

A. Verified architectural decisions
B. Proposed/default decisions
C. Open decisions
D. Inconsistencies
E. ADRs that must be resolved before implementation
F. Assumptions allowed for the pilot
G. Explicitly excluded scope


============================================================
PART 2 — PILOT SUCCESS DEFINITION
============================================================

Define exactly what "DisputeIQ Pilot Complete" means.

Include:

- functional completion
- all three dispute categories
- complete 11-stage workflow
- controlled RAG
- deterministic rules
- HITL
- Model Gateway
- auditability
- observability
- evaluation
- security baseline
- CI/CD
- Cloudflare deployment
- documentation
- demo scenario


============================================================
PART 3 — DELIVERY ROADMAP
============================================================

Provide:

Sprint 0 / Pre-development preparation if necessary

Sprint 1 — Weeks 1–2
Sprint 2 — Weeks 3–4
Sprint 3 — Weeks 5–6
Sprint 4 — Weeks 7–8
Sprint 5 — Weeks 9–10

Optional:
Sprint 6 — Weeks 11–12

For every sprint provide:

1. Sprint objective
2. Architecture capabilities delivered
3. Functional requirements delivered
4. OpenSpec capabilities affected
5. OpenSpec change IDs
6. Backend work
7. Frontend work
8. LangGraph work
9. Database work
10. RAG work
11. AI / Model Gateway work
12. Deterministic services/rules work
13. HITL work
14. Security work
15. Observability work
16. Testing/evaluation work
17. GitHub Actions work
18. Documentation/ADR work
19. Demonstrable sprint outcome
20. Exit criteria
21. Dependencies
22. Risks
23. Technical debt intentionally deferred


============================================================
PART 4 — WEEK-BY-WEEK EXECUTION
============================================================

Within every sprint break work into individual weeks.

For each week identify:

- objective
- OpenSpec change
- capability being learned
- feature being implemented
- important files/modules expected to change
- tests required
- GitHub workflow required
- expected demonstration
- exit gate

Do NOT assign arbitrary daily estimates.

Use dependency-driven sequencing.


============================================================
PART 5 — OPENSPEC CHANGE MAP
============================================================

Recommend the complete ordered OpenSpec change sequence.

Start by evaluating this baseline:

001-platform-foundation
002-controlled-policy-rag
003-stateful-langgraph-workflow
004-model-gateway-ai-capabilities
005-deterministic-controls-hitl
006-security-audit-communication
007-observability-evaluation-business-expansion
008-deployment-hardening-pilot

Determine whether these changes should remain intact or be divided
further for a 10-week learning-focused implementation.

For each recommended change provide:

Change ID
Name
Problem addressed
FR IDs
Affected capability specs
Dependencies
Architecture components
Implementation scope
Non-goals
Required GWT scenarios
Testing strategy
Definition of Done
Demo outcome


============================================================
PART 6 — LANGGRAPH IMPLEMENTATION ROADMAP
============================================================

Show exactly when and how to implement:

DisputeIQState
graph.py
routing.py
interrupts.py

and nodes:

n01_intake
n02_classify
n03_context
n04_evidence
n05_policy
n06_rules
n07_confidence
n08_recommendation
n09_human_decision
n10_communication
n11_finalize

For each node identify:

Execution mode:
- deterministic
- tool
- hybrid
- AI-assisted
- HITL

Inputs
Outputs
State slice modified
Domain service used
External dependency
Failure paths
Retry strategy
Interrupt conditions
Checkpoint behaviour
Idempotency requirement
Audit events
Tests required


============================================================
PART 7 — CONTROLLED RAG LEARNING ROADMAP
============================================================

Do NOT reduce RAG to simple vector similarity search.

Plan implementation for:

Policy source
   ↓
ingestion
   ↓
normalization
   ↓
chunking
   ↓
metadata enrichment
   ↓
embedding
   ↓
pgvector
   ↓
deterministic applicability filters
   ↓
lexical retrieval
   +
vector retrieval
   ↓
candidate fusion
   ↓
reranking
   ↓
context assembly
   ↓
citation generation
   ↓
confidence gate
   ↓
LangGraph

Include:

- effective dating
- dispute type
- product
- jurisdiction metadata where appropriate
- policy version
- chunk ID
- source lineage
- retrieval score
- reranker score
- citation correctness
- low-confidence policy review

Define an RAG evaluation dataset and metrics.

Include:

Recall@K
Precision@K
MRR/NDCG if useful
effective-date correctness
citation correctness
grounded-answer quality
low-confidence routing accuracy


============================================================
PART 8 — MODEL GATEWAY ROADMAP
============================================================

Design an incremental implementation plan for the provider-neutral
Model Gateway.

It must eventually provide:

Application capability
        ↓
Model Gateway
        ↓
prompt/version resolver
        ↓
data/PII policy
        ↓
token budget
        ↓
provider routing
        ↓
model execution
        ↓
timeout/retry
        ↓
fallback
        ↓
structured output validation
        ↓
guardrails
        ↓
telemetry

Do not tightly couple application code to OpenAI or another provider.

Show when to add:

- provider interface
- provider adapter
- model aliases
- prompt registry
- response schemas
- token usage tracking
- latency tracking
- fallback
- safety validation
- cost telemetry


============================================================
PART 9 — DETERMINISTIC DECISIONING
============================================================

Identify everything that must remain outside the LLM.

At minimum cover:

- intake validation
- idempotency
- required evidence
- evidence completeness
- policy applicability
- timeline rules
- eligibility rules
- decision rules
- confidence thresholds
- escalation
- authorization
- state transitions
- final validation

Show the recommended Python package/interface structure and when each
piece should be implemented.


============================================================
PART 10 — HITL ROADMAP
============================================================

Plan:

- manual classification
- additional evidence request
- policy review
- manual rule review
- supervisor review
- final decision
- approve
- modify
- reject
- rework
- durable interrupt
- checkpoint
- resume
- stale action protection
- optimistic concurrency
- segregation of duties

Include E2E tests proving that already completed external side effects
are NOT repeated after resume.


============================================================
PART 11 — DATABASE & STATE ROADMAP
============================================================

Plan separate logical persistence for:

A. PostgreSQL Business State
B. PostgreSQL LangGraph Checkpoint State
C. pgvector Policy Knowledge
D. Immutable Audit
E. Redis transient coordination
F. R2/Object Storage

Show:

- schema sequence
- Alembic migration sequence
- entities introduced by sprint
- indexing
- optimistic locking
- idempotency constraints
- audit event design
- retention assumptions
- backup/restore testing


============================================================
PART 12 — FRONTEND ROADMAP
============================================================

Avoid building a polished UI too early.

Plan an incremental React/TypeScript UI for:

- case creation
- case list
- case details
- workflow status
- evidence
- policy citations
- rule outcomes
- recommendation
- confidence
- reviewer task queue
- human decision UI
- timeline/audit view
- operational dashboard if appropriate

Separate:

MVP UI
PILOT UI
POST-PILOT UI


============================================================
PART 13 — TEST STRATEGY
============================================================

Create a testing pyramid covering:

Unit
Contract
Integration
Workflow
Determinism
RAG evaluation
AI evaluation
Security
Resilience
Performance
End-to-end
Audit reconstruction

Map test categories to sprints.

Start tests in Sprint 1.
Do NOT postpone testing to the final sprint.


============================================================
PART 14 — AI EVALUATION ROADMAP
============================================================

Plan evaluation datasets for:

classification
evidence extraction
policy retrieval
citation
recommendation grounding
communication safety
prompt injection
fallback behaviour

Start with the FRD recommended corpus and explain how to expand it
during pilot development.

Define measurable thresholds where the documents provide them.
Where they do not, mark thresholds as PROPOSED and do not pretend
they are requirements.


============================================================
PART 15 — GITHUB ACTIONS ROADMAP
============================================================

Plan implementation of:

pr-validation.yml
backend-ci.yml
frontend-ci.yml
graph-tests.yml
rag-evaluation.yml
ai-evaluation.yml
security-scan.yml
deploy.yml

Explain:

- triggering conditions
- required checks
- fast PR checks
- expensive nightly/manual AI evaluations
- branch protection
- release gate
- deployment approvals


============================================================
PART 16 — OBSERVABILITY ROADMAP
============================================================

Show incremental integration of:

OpenTelemetry
LangSmith
LangWatch

Define:

Trace IDs
correlation IDs
case IDs
workflow_run_id
model_invocation_id

Track at minimum:

- API latency
- workflow duration
- node latency
- retries
- node failures
- checkpoint failures
- HITL wait times
- RAG quality
- AI quality
- model latency
- token consumption
- provider fallback
- schema rejection
- grounding failure
- rule exceptions
- audit failures


============================================================
PART 17 — LEARNING MATRIX
============================================================

This is extremely important.

Because this is my first end-to-end production-style GenAI project,
identify what I should LEARN while implementing each sprint.

Create:

Sprint
Technology
Concept
What I should implement myself
What Codex may accelerate
What I should NOT blindly delegate to Codex
Proof that I understand it

Explicitly include:

- OpenSpec
- Pydantic v2
- FastAPI
- async Python
- PostgreSQL
- Alembic
- pgvector
- embeddings
- chunking
- metadata filtering
- hybrid search
- reranking
- RAG evaluation
- LangGraph StateGraph
- typed state
- conditional routing
- checkpointing
- interrupt/resume
- HITL
- deterministic rule engines
- Model Gateway
- structured LLM outputs
- prompt versioning
- provider abstraction
- Redis
- object storage
- OpenTelemetry
- LangSmith
- LangWatch
- Docker
- GitHub Actions
- AI security
- AI evaluation


============================================================
PART 18 — CLOUDFLARE DEPLOYMENT ROADMAP
============================================================

Do NOT assume the Python/FastAPI/LangGraph backend should execute
inside Cloudflare Workers.

Follow the hybrid architecture:

Internet
   ↓
Cloudflare
   - DNS
   - WAF
   - DDoS
   - Rate limiting
   - Zero Trust
   - Pages where appropriate
   ↓
Containerized application backend
   ↓
FastAPI
   ↓
LangGraph workers
   ↓
PostgreSQL / pgvector
Redis
R2
Model Gateway

Determine what reasonably belongs on Cloudflare:

- DNS
- WAF
- rate limiting
- Zero Trust
- frontend hosting if appropriate
- R2
- optional Worker-based edge functions

Determine what requires a container-capable origin:

- FastAPI
- LangGraph workers
- Python services
- long-running workflows

Include deployment stages:

local
    ↓
Docker Compose

development
    ↓
CI environment

staging
    ↓
production-like environment

pilot
    ↓
Cloudflare edge + secured backend origin

Include:

secrets
health endpoints
container registry
database migration
rollback
smoke test
backup/restore
WAF rules
TLS
CORS
rate limiting
Zero Trust
observability
manual promotion


============================================================
PART 19 — SECURITY ROADMAP
============================================================

Plan incremental controls for:

- authentication
- authorization / RBAC
- IDOR protection
- PII minimization
- secrets
- encryption
- input validation
- evidence upload
- malware/content validation
- prompt injection
- tool authorization
- model provider egress
- audit access
- model data policy
- dependency scanning
- SAST
- container scanning


============================================================
PART 20 — ADR ROADMAP
============================================================

Review all ADR candidates in FRD/HLD/LLD.

Categorize them:

MUST DECIDE BEFORE CODING
MUST DECIDE BEFORE FEATURE
CAN DEFER UNTIL HARDENING
POST-PILOT

For each ADR provide:

Decision
Options
Recommended pilot choice
Reason
Consequences
Revisit trigger


============================================================
PART 21 — DEPENDENCY / CRITICAL PATH
============================================================

Generate the implementation dependency graph.

Example:

Project Foundation
       ↓
Contracts / State / DB
       ↓
Case API
       ↓
LangGraph Skeleton
       ↓
Authoritative Providers
       ↓
Policy RAG
       ↓
Rules
       ↓
Confidence
       ↓
Recommendation
       ↓
HITL
       ↓
Communication
       ↓
Audit
       ↓
Full E2E
       ↓
UPI + ATM expansion
       ↓
Hardening
       ↓
Deployment

Correct this based on FRD/HLD/LLD.

Identify the true critical path.


============================================================
PART 22 — RISK REGISTER
============================================================

Identify pilot risks including:

- over-engineering
- OpenSpec change too large
- excessive AI scope
- RAG quality
- LangGraph state complexity
- HITL complexity
- checkpoint/resume defects
- inconsistent deterministic rules
- AI non-determinism
- evaluation gaps
- Cloudflare/runtime mismatch
- deployment complexity
- security
- observability
- cost/token usage
- feature creep

For each:

Probability
Impact
Mitigation
Sprint where addressed


============================================================
PART 23 — DEFINITION OF DONE
============================================================

Create:

Change DoD
Story/task DoD
Sprint DoD
MVP DoD
Pilot DoD

A feature is NOT complete merely because the code works.

Completion must consider where relevant:

specification
code
tests
evaluation
security
observability
audit
documentation
CI
traceability


============================================================
PART 24 — TRACEABILITY MATRIX
============================================================

Create a planning matrix:

FR ID
Requirement
OpenSpec capability
OpenSpec Change ID
Sprint
Architecture component
LangGraph node
Implementation package
Test type
Evaluation type
GitHub workflow
Status

Do not omit Must requirements.


============================================================
PART 25 — 8 vs 10 vs 12 WEEK COMPARISON
============================================================

Give me three scenarios:

8-WEEK MVP
10-WEEK RECOMMENDED PILOT
12-WEEK LEARNING + HARDENED PILOT

For each show:

- scope
- compromises
- learning depth
- deployment state
- evaluation depth
- technical debt
- production-readiness level

Then recommend ONE plan for me.


============================================================
PART 26 — FIRST IMPLEMENTATION ACTIONS
============================================================

Finish with an exact ordered checklist for what I should do next.

For example:

Step 1
Resolve blocking ADRs

Step 2
Create/reconcile repository structure

Step 3
Initialize OpenSpec project

Step 4
Create long-lived capability specifications

Step 5
Create first OpenSpec change

Step 6
Review proposal

Step 7
Generate/change design

Step 8
Generate tasks

Step 9
Review implementation plan

Step 10
Only then ask Codex to start implementation

Specify the exact recommended first OpenSpec change and its
initial deliverables.

STOP after producing the implementation blueprint.

DO NOT write production application code.
DO NOT automatically create every OpenSpec change.
DO NOT start implementing features.

I want to review and approve the delivery plan first.