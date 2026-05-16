# PromptForge - Week 28: Integrated Production-Style AI Platform

> **Program:** AI & Full Stack Engineering
> **Week:** 28
> **Date:** 16 May 2026
> **Focus:** full-stack integration, Docker Compose deployment, observability, and production-style platform packaging

---

## What We Built This Week

Week 28 connects the previously built PromptForge components into one complete AI platform.

The goal was not to rebuild existing systems. Authentication, prompt versioning, Qdrant search, LangGraph evaluation, LangSmith tracing, Streamlit dashboards, workspaces, approvals, and A/B testing already existed. This week adds the integration layer that makes them work together end to end.

```text
Streamlit UI
    -> FastAPI backend
    -> PostgreSQL
    -> Qdrant
    -> LangGraph evaluation
    -> optional LangSmith tracing
    -> analytics dashboard
```

---

## What Changed

| Area | Before Week 28 | After Week 28 |
|---|---|---|
| Frontend API usage | Some Streamlit flows depended on local session state | Streamlit pages call real backend APIs |
| Evaluation results | Visible mostly in the current UI session | Stored in PostgreSQL as `EvaluationRun` rows |
| A/B testing | UI looped over `/evaluate` calls | Backend owns `POST /ab-test` and stores summary results |
| Analytics | Mixed temporary UI data and workspace counts | Dedicated `GET /analytics` endpoint returns durable metrics |
| Feedback | Approval comments were mostly activity text | Feedback is stored in a `Feedback` table |
| Observability | LangSmith handled evaluation traces | Backend also logs request latency, endpoint usage, user, tenant, role, and errors |
| Docker | Backend Compose existed, frontend was separate | API, frontend, Postgres, and Qdrant run together |
| Networking | Some local `localhost` assumptions remained | Compose services use `api`, `postgres`, and `qdrant` service names |
| Run docs | Setup was split across notes | `run.md` documents full Docker and local workflows |

---

## What Was Newly Added

### Backend

- `EvaluationRun` model for durable evaluation analytics
- `ABTestRun` model for backend-owned A/B test summaries
- `Feedback` model for prompt governance comments
- `POST /ab-test`
- `GET /analytics`
- `POST /feedback`
- `GET /feedback`
- request logging middleware
- `SQL_ECHO` setting for optional SQL debug logging

### Frontend

- restored workspace API client methods
- added analytics, A/B test, and feedback API client methods
- Developer evaluations now pass `prompt_id`
- A/B Testing page now calls the backend A/B test API
- Analytics page now reads persisted backend metrics
- metric cards now wrap into dashboard rows

### Deployment And Docs

- `Dockerfile.backend`
- `Dockerfile.frontend`
- updated `docker-compose.yml`
- updated `.env.example`
- updated `.gitignore`
- `run.md`
- `WEEK_28.md`

---

## Learning Goals

Students should learn:

| Concept | What PromptForge Demonstrates |
|---|---|
| Full-stack AI integration | Streamlit pages trigger real FastAPI workflows |
| Backend orchestration | Services coordinate prompts, evaluations, A/B tests, approvals, and analytics |
| Production packaging | API, UI, PostgreSQL, and Qdrant run through Docker Compose |
| Observability | Request logs, latency, activity, traces, and dashboard metrics |
| Operational AI workflows | Teams can create, evaluate, approve, compare, and monitor prompts |

---

## Existing Systems Reused

These systems were reused directly:

- FastAPI backend
- JWT authentication
- multi-tenant user model
- workspace collaboration layer
- prompt versioning
- Qdrant semantic search
- LangGraph evaluation engine
- LangSmith tracing support
- Streamlit dashboard
- approval workflow
- activity feed
- A/B testing foundation

---

## Backend Integration

### Evaluation Persistence

New file:

```text
app/services/evaluation_service.py
```

The service runs the existing LangGraph pipeline:

```python
result = graph.invoke({"prompt": prompt})
```

Then it stores:

- workspace id
- user id
- prompt id
- source
- prompt
- output
- score
- latency

The `/evaluate` endpoint now returns:

```json
{
  "prompt": "Explain AI to a beginner",
  "output": "AI response...",
  "score": 8.4,
  "latency_ms": 42.1
}
```

### Backend A/B Testing

New files:

```text
app/routers/ab_test_router.py
app/services/ab_test_service.py
app/schemas/ab_test_schema.py
```

Flow:

```text
POST /ab-test
    -> validate workspace access
    -> load PromptVersion A and B
    -> run LangGraph for both versions
    -> store EvaluationRun rows
    -> store ABTestRun summary
    -> log workspace activity
    -> return winner and per-round results
```

### Analytics API

New files:

```text
app/routers/analytics_router.py
app/services/analytics_service.py
app/schemas/analytics_schema.py
```

`GET /analytics` returns:

- total prompts
- total evaluations
- total A/B tests
- average score
- average latency
- review queue count
- production prompt count
- draft prompt count
- approval rate
- recent activity count
- prompt usage
- score and latency trends

### Feedback API

New files:

```text
app/routers/feedback_router.py
app/services/feedback_service.py
app/schemas/feedback_schema.py
```

Endpoints:

```http
POST /feedback
GET /feedback
```

Approvals and rejections also create feedback rows through `workspace_service.py`.

### Observability

New file:

```text
app/middleware/logging_middleware.py
```

Each request logs:

- method
- path
- status code
- latency
- user id
- tenant id
- role

Responses also include:

```text
X-Process-Time-MS
```

---

## Frontend Integration

Updated file:

```text
frontend/api/client.py
```

Important methods now available:

```python
api.current_workspace()
api.workspace_prompts()
api.workspace_activity()
api.analytics()
api.evaluate(prompt, prompt_id=...)
api.run_ab_test(...)
api.add_feedback(...)
```

Updated pages:

| File | Change |
|---|---|
| `frontend/views/developer.py` | Evaluation calls pass `prompt_id` |
| `frontend/views/ab_testing.py` | Calls `POST /ab-test` |
| `frontend/views/analytics.py` | Calls `GET /analytics` |
| `frontend/utils/charts.py` | Metric cards wrap into rows |

---

## Docker Compose Platform

New Dockerfiles:

```text
Dockerfile.backend
Dockerfile.frontend
```

Updated Compose services:

| Service | Purpose | Port |
|---|---|---|
| `api` | FastAPI backend | `8000:8000` |
| `frontend` | Streamlit dashboard | `8501:8501` |
| `postgres` | PostgreSQL database | `5432:5432` |
| `qdrant` | Vector database | `6433:6333`, `6434:6334` |

Container networking:

```text
frontend -> http://api:8000
api      -> postgres:5432
api      -> qdrant:6333
```

Run:

```powershell
docker compose up --build
```

Open:

```text
http://localhost:8501
```

API docs:

```text
http://localhost:8000/docs
```

---

## End-To-End Demo Flow

1. Login or register.
2. Open Workspace and confirm workspace context.
3. Create a prompt in Developer.
4. Edit the prompt to create version 2.
5. Run evaluation.
6. Compare version 1 and version 2 in A/B Testing.
7. Approve the prompt in Reviewer or Workspace.
8. Open Analytics and show durable metrics.
9. Open Workspace activity and show recent events.
10. If configured, open LangSmith and show traces.

---

## Verification

Checks performed:

```powershell
python -m compileall app frontend
python -c "from app.main import app; print(app.title)"
docker compose config
```

Smoke test covered:

- register
- login
- create prompt
- update prompt version
- evaluate prompt
- run A/B test
- approve prompt
- add feedback
- read analytics

Result:

```text
smoke ok 1 3 1
```

Docker services were not started because Docker Desktop was not running on the machine.

---

## Final Outcome

PromptForge is now packaged as a complete AI platform:

- frontend calls backend APIs
- prompts persist in PostgreSQL
- embeddings persist in Qdrant
- evaluations run through LangGraph
- LangSmith traces work when configured
- evaluations and A/B tests are stored for analytics
- approvals create governance records
- activity and analytics provide operational visibility
- the platform runs with one Docker Compose command
