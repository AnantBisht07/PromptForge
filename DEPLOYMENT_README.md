# PromptForge Deployment README

This guide explains how to deploy PromptForge as a free or low-cost demo platform.

PromptForge has four runtime parts:

```text
Streamlit frontend
FastAPI backend
PostgreSQL database
Qdrant vector database
```

Do not deploy `docker-compose.yml` directly to a serverless host. Docker Compose is for local development. In cloud deployment, each service runs separately.

---

## Recommended Free Demo Architecture

Use this setup:

```text
Streamlit Community Cloud
        |
        v
Render FastAPI backend
        |
        +--> Neon PostgreSQL
        |
        +--> Qdrant Cloud
        |
        +--> Optional LangSmith
```

| Component | Service | Why |
|---|---|---|
| Frontend | Streamlit Community Cloud | Best free host for Streamlit apps |
| Backend | Render Web Service | Simple Docker deployment for FastAPI |
| SQL database | Neon | Free serverless PostgreSQL |
| Vector database | Qdrant Cloud | Free cluster for vector search demos |
| Tracing | LangSmith | Optional evaluation traces |
| LLM | OpenAI | Optional; app works with mock LLM when empty |

---

## What Not To Include In GitHub

Never commit these:

```text
.env
OPENAI_API_KEY
LANGCHAIN_API_KEY
QDRANT_API_KEY
SECRET_KEY production value
Neon database password
local SQLite database files
Docker volumes
__pycache__
.pytest_cache
local smoke test databases
private live scripts
```

These are already ignored or should stay local:

```text
.env
.env.*
promptforge.db
promptforge_smoke_*.db
*.sqlite3
__pycache__/
.pytest_cache/
```

Use `.env.example` for variable names only. Put real values inside hosting provider dashboards.

---

## Files That Matter For Deployment

| File | Purpose |
|---|---|
| `Dockerfile.backend` | Render backend container |
| `Dockerfile.frontend` | Local Docker frontend container |
| `docker-compose.yml` | Local full-stack run only |
| `.env.example` | Environment variable template |
| `frontend/dashboard.py` | Streamlit entrypoint |
| `frontend/api/client.py` | Frontend API client |
| `app/core/config.py` | Backend environment settings |
| `app/services/vector_service.py` | Qdrant connection logic |

---

## Code Updates Required For Cloud

The current code already supports Qdrant Cloud. If your copy is older, check these files.

### 1. `app/core/config.py`

Make sure these settings exist:

```python
QDRANT_URL: str = ""
QDRANT_API_KEY: str = ""
QDRANT_HOST: str = "localhost"
QDRANT_PORT: int = 6333
QDRANT_COLLECTION: str = "prompts"
```

Why:

- local Docker uses `QDRANT_HOST` and `QDRANT_PORT`
- Qdrant Cloud uses `QDRANT_URL` and `QDRANT_API_KEY`

### 2. `app/services/vector_service.py`

Make sure Qdrant client creation supports both local and cloud:

```python
if settings.QDRANT_URL:
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )
else:
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )
```

### 3. `.env.example`

Make sure these variables are documented:

```text
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 4. `frontend/api/client.py`

The frontend must read backend URL from:

```text
PROMPTFORGE_API_URL
```

For Streamlit Cloud this should point to Render:

```text
PROMPTFORGE_API_URL=https://your-render-api.onrender.com
```

---

## Step 1: Push Clean Code To GitHub

Before deploying, commit only deployable files.

Check status:

```powershell
git status --short
```

Do not stage deleted or private files accidentally.

Add intended files:

```powershell
git add app/core/config.py app/services/vector_service.py .env.example docker-compose.yml DEPLOYMENT_README.md README.md
```

Commit:

```powershell
git commit -m "Add deployment guide and Qdrant cloud config"
```

Push:

```powershell
git push origin main
```

---

## Step 2: Create Neon PostgreSQL

1. Go to Neon.
2. Create a free project.
3. Create a database.
4. Copy the connection string.

It looks like:

```text
postgresql://user:password@host.neon.tech/dbname?sslmode=require
```

Use it as:

```text
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
```

Do not paste this URL into GitHub files.

---

## Step 3: Create Qdrant Cloud Cluster

1. Go to Qdrant Cloud.
2. Create a free cluster.
3. Copy the cluster URL.
4. Create/copy the API key.

Use:

```text
QDRANT_URL=https://your-cluster-url.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=prompts
EMBEDDING_DIM=384
```

Do not include the API key in GitHub.

---

## Step 4: Deploy Backend On Render

Create a new Render Web Service.

Use these settings:

```text
Repository: AnantBisht07/PromptForge
Branch: main
Runtime: Docker
Dockerfile path: Dockerfile.backend
Port: 8000
```

Add environment variables in Render:

```text
SECRET_KEY=generate-a-strong-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=your-neon-postgres-url
SQL_ECHO=false
QDRANT_URL=your-qdrant-cloud-url
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=prompts
EMBEDDING_DIM=384
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=promptforge-eval
```

For mock LLM mode, leave:

```text
OPENAI_API_KEY=
```

For LangSmith traces, set:

```text
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=promptforge-eval
```

After deploy, Render gives a URL like:

```text
https://promptforge-api.onrender.com
```

Test backend:

```text
https://promptforge-api.onrender.com/
https://promptforge-api.onrender.com/docs
```

Expected health response:

```json
{
  "message": "PromptForge API is running",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

---

## Step 5: Deploy Frontend On Streamlit Community Cloud

Create a new Streamlit app.

Use:

```text
Repository: AnantBisht07/PromptForge
Branch: main
Main file path: frontend/dashboard.py
```

Add Streamlit secret/environment value:

```text
PROMPTFORGE_API_URL=https://promptforge-api.onrender.com
```

Replace the URL with your actual Render backend URL.

Deploy.

Streamlit gives a URL like:

```text
https://promptforge.streamlit.app
```

---

## Step 6: Test The Live Deployment

Open the Streamlit URL and test:

1. Register user.
2. Login.
3. Create workspace.
4. Create prompt.
5. Edit prompt to create version 2.
6. Run evaluation.
7. Run A/B test.
8. Approve prompt.
9. Add feedback.
10. Open Analytics.
11. Check Activity feed.

Expected:

```text
Prompt create works
Version history shows v1 and v2
Evaluation returns output, score, latency
A/B test returns winner
Approval moves prompt to production
Analytics count evaluations and A/B tests
Activity feed shows events
```

---

## Deployment Smoke Test Endpoints

Replace `API_URL` with your Render URL.

Health:

```powershell
Invoke-RestMethod https://your-api.onrender.com/
```

Docs:

```text
https://your-api.onrender.com/docs
```

Streamlit:

```text
https://your-app.streamlit.app
```

Qdrant is tested indirectly when prompt creation and semantic search work.

---

## Common Deployment Problems

### 1. Render backend sleeps

Render free web services can sleep after inactivity. First request may be slow.

Explain to students:

> "Free hosting is fine for demos, but production needs always-on paid infrastructure."

### 2. Streamlit cannot login

Usually `PROMPTFORGE_API_URL` is wrong.

Check Streamlit secrets:

```text
PROMPTFORGE_API_URL=https://your-render-api.onrender.com
```

No trailing slash is required.

### 3. Backend cannot connect to Postgres

Check:

```text
DATABASE_URL
```

For Neon it should include:

```text
sslmode=require
```

### 4. Backend cannot connect to Qdrant

Check:

```text
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION
```

If `QDRANT_URL` is empty, the backend falls back to local `QDRANT_HOST` and `QDRANT_PORT`.

### 5. Prompt creation fails

Prompt creation touches both PostgreSQL and Qdrant:

```text
PostgreSQL stores prompt/version
Qdrant stores vector
ActivityLog stores event
```

So check database URL and Qdrant credentials.

### 6. Analytics is empty

Run an evaluation first. Analytics needs stored `EvaluationRun` and `ABTestRun` rows.

---

## What To Explain To Students

Use this explanation:

```text
Local development:
docker compose runs everything together.

Cloud deployment:
each service is hosted separately.
```

Cloud architecture:

```text
Streamlit Cloud
  -> Render FastAPI
       -> Neon Postgres
       -> Qdrant Cloud
       -> Optional LangSmith
```

Main lesson:

> "Serverless deployment means using managed services and connecting them with environment variables."

---

## Final Checklist

Before sharing the deployed app:

- `SECRET_KEY` is strong.
- `.env` is not committed.
- `DATABASE_URL` is set in Render only.
- `QDRANT_API_KEY` is set in Render only.
- `PROMPTFORGE_API_URL` is set in Streamlit Cloud.
- Backend `/docs` opens.
- Streamlit app opens.
- Prompt create works.
- Evaluation works.
- A/B test works.
- Analytics works.

---

## Production Notes

This deployment is good for demos and student projects.

For real production, upgrade:

- paid always-on backend hosting
- managed Postgres with backups
- paid Qdrant cluster
- real embedding model
- real LLM provider key
- CORS policy
- migrations instead of `create_all`
- monitoring and alerting
- custom domain
- HTTPS-only secrets and rotation
