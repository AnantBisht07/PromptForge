# Running PromptForge

This guide runs the complete PromptForge platform: FastAPI backend, Streamlit UI, PostgreSQL, Qdrant, workspaces, approvals, evaluation, A/B testing, analytics, and optional LangSmith tracing.

## One-command Docker run

From the repo root:

```powershell
docker compose up --build
```

Open:

- Streamlit UI: `http://localhost:8501`
- FastAPI docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/`
- Qdrant host port: `http://localhost:6433`
- PostgreSQL host port: `localhost:5432`

Docker Compose starts:

| Service | Purpose | Internal address |
|---|---|---|
| `frontend` | Streamlit dashboard | calls `http://api:8000` |
| `api` | FastAPI backend | `http://api:8000` |
| `postgres` | SQL database | `postgres:5432` |
| `qdrant` | Vector database | `qdrant:6333` |

Stop:

```powershell
docker compose down
```

Reset all Docker data:

```powershell
docker compose down -v
```

## Environment

Use `.env.example` as the template. The local `.env` file is ignored by Git.

Important variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | Local backend database URL |
| `POSTGRES_PASSWORD` | Docker Postgres password |
| `POSTGRES_DB` | Docker Postgres database |
| `QDRANT_HOST` | Vector database host |
| `PROMPTFORGE_API_URL` | Streamlit backend URL |
| `OPENAI_API_KEY` | Optional real LLM key |
| `LANGCHAIN_API_KEY` | Optional LangSmith tracing key |
| `LANGCHAIN_PROJECT` | LangSmith project name |

Inside Docker Compose, the backend uses service names:

```text
DATABASE_URL=postgresql://postgres:password@postgres:5432/promptforge
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

The frontend uses:

```text
PROMPTFORGE_API_URL=http://api:8000
```

## Local backend and UI

Start only infrastructure:

```powershell
docker compose up -d postgres qdrant
```

Run backend:

```powershell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/promptforge"
$env:QDRANT_HOST="localhost"
$env:QDRANT_PORT="6433"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run frontend:

```powershell
$env:PROMPTFORGE_API_URL="http://localhost:8000"
streamlit run frontend/dashboard.py
```

## UI demo flow

1. Open `http://localhost:8501`.
2. Register or login.
3. Create or use a workspace.
4. Add team members by username.
5. Create a prompt in Developer.
6. Edit it to create a new version.
7. Run evaluation.
8. Compare versions in A/B Testing.
9. Approve or reject in Reviewer or Workspace.
10. View Analytics.
11. View Workspace activity.

## Main API flows

Create prompt:

```text
Streamlit -> /prompts/create -> PostgreSQL prompt/version -> Qdrant vector -> ActivityLog
```

Run evaluation:

```text
Streamlit -> /evaluate -> LangGraph -> optional LangSmith trace -> EvaluationRun -> Analytics
```

Run A/B test:

```text
Streamlit -> /ab-test -> LangGraph per version -> EvaluationRun + ABTestRun -> Analytics
```

Approve prompt:

```text
Reviewer UI -> /prompts/approve -> production status -> Feedback -> ActivityLog
```

## Important endpoints

| Endpoint | Purpose |
|---|---|
| `POST /auth/register` | Create user |
| `POST /auth/login` | Login and receive JWT |
| `GET /users/me` | Current user and workspace |
| `POST /workspace/create` | Create workspace |
| `POST /workspace/add-member` | Add team member |
| `GET /workspace/prompts` | Shared prompts |
| `GET /workspace/activity` | Recent workspace activity |
| `POST /prompts/create` | Create prompt |
| `PUT /prompts/{prompt_id}` | Create new prompt version |
| `POST /prompts/approve` | Move prompt to production |
| `POST /prompts/reject` | Move prompt to draft |
| `POST /evaluate` | Run LangGraph evaluation |
| `POST /ab-test` | Compare prompt versions |
| `GET /analytics` | Platform analytics |
| `POST /feedback` | Add prompt feedback |

## Troubleshooting

If Docker shows:

```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified
```

Start Docker Desktop, then run:

```powershell
docker compose up --build
```

If the local UI cannot reach the backend:

```powershell
$env:PROMPTFORGE_API_URL="http://localhost:8000"
```

If local backend cannot reach Qdrant, remember Compose maps Qdrant to host port `6433`:

```powershell
$env:QDRANT_HOST="localhost"
$env:QDRANT_PORT="6433"
```
