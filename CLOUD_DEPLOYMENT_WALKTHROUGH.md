# PromptForge Cloud Deployment Walkthrough

Use this file when deploying PromptForge after creating accounts on:

- Qdrant Cloud
- Neon
- Streamlit Community Cloud
- Render

This is the practical step-by-step guide for the live deployment flow.

---

## Important Rule

Never paste real secrets into GitHub files.

Do not commit:

```text
.env
DATABASE_URL with real password
QDRANT_API_KEY
OPENAI_API_KEY
LANGCHAIN_API_KEY
SECRET_KEY production value
Streamlit secrets.toml
local database files
Docker volumes
private scripts
```

Use GitHub only for code and placeholder examples. Real values go into Render and Streamlit dashboards.

---

## Final Cloud Architecture

PromptForge is deployed as separate services:

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

Explain this to students:

```text
The frontend does not store prompts.
The frontend calls the backend.
The backend stores relational data in Postgres.
The backend stores embeddings in Qdrant.
Analytics, approvals, evaluations, and workspace activity all flow through backend APIs.
```

---

## Step 1: Finish Neon PostgreSQL

You already created the Neon project.

From the Neon screen:

1. Click `Show password`.
2. Copy the full connection string.
3. Keep it private.

It should look like this:

```text
postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
```

Use this value later in Render as:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
```

Do not paste the real Neon URL into:

```text
README.md
DEPLOYMENT_README.md
CLOUD_DEPLOYMENT_WALKTHROUGH.md
.env.example
GitHub commits
student shared notes
```

For this project, use the normal connection string first. If the app later has many concurrent users, Neon also supports pooled connection strings.

---

## Step 2: Create Qdrant Free Cluster

From your Qdrant Cloud screen:

1. Stay on `Clusters`.
2. Under `Create a Free Cluster`, enter a cluster name.

Recommended name:

```text
promptforge-free
```

3. Keep the free cluster plan.
4. Choose a region close to the backend if Qdrant gives a choice.
5. Click `Create Free Cluster`.
6. Wait until the cluster status is ready or healthy.

When Qdrant shows the API key after cluster creation:

1. Copy it immediately.
2. Store it privately.
3. Do not commit it.

You also need the cluster URL. It should look like:

```text
https://your-cluster-id.region.aws.cloud.qdrant.io
```

Use these later in Render:

```text
QDRANT_URL=https://your-cluster-id.region.aws.cloud.qdrant.io
QDRANT_API_KEY=your-private-qdrant-api-key
QDRANT_COLLECTION=prompts
EMBEDDING_DIM=384
```

Important:

- Use the Qdrant cluster URL, not the browser dashboard URL.
- Use a Qdrant cluster/data API key, not your Qdrant login password.
- You do not need to manually create the `prompts` collection for the demo; the backend can create it when vector search is used.

---

## Step 3: Deploy Backend On Render

Streamlit only hosts the UI. PromptForge also needs a backend server, so deploy FastAPI on Render.

Go to Render and create a new Web Service.

Use these settings:

```text
Repository: AnantBisht07/PromptForge
Branch: main
Runtime: Docker
Dockerfile path: Dockerfile.backend
Root directory: leave blank
Build command: leave blank
Start command: leave blank
Plan: Free is okay for demo
```

Render will use the `CMD` from `Dockerfile.backend`:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Add these environment variables in Render.

Required:

```text
PORT=8000
SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=your-neon-postgres-connection-string
SQL_ECHO=false
QDRANT_URL=your-qdrant-cloud-url
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=prompts
EMBEDDING_DIM=384
```

Optional:

```text
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=promptforge-eval
```

For class demo mode, you can leave `OPENAI_API_KEY` empty if the app is using mock evaluation behavior.

Do not add real secrets to code files. Add them only in Render's environment variable panel.

After Render deploys, copy the backend URL. It will look like:

```text
https://promptforge-api.onrender.com
```

Test these URLs:

```text
https://promptforge-api.onrender.com/
https://promptforge-api.onrender.com/docs
```

Expected root response:

```json
{
  "message": "PromptForge API is running",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

If `/docs` opens, the backend is running.

---

## Step 4: Deploy Frontend On Streamlit Community Cloud

Go to Streamlit Community Cloud.

Create a new app:

```text
Repository: AnantBisht07/PromptForge
Branch: main
Main file path: frontend/dashboard.py
```

The repo includes:

```text
runtime.txt
```

This tells Streamlit Cloud to use Python 3.11, matching the Dockerfiles.

Open `Advanced settings`.

In the secrets field, add:

```toml
PROMPTFORGE_API_URL = "https://your-render-backend-url.onrender.com"
```

Replace the URL with your actual Render backend URL.

Do not put Neon, Qdrant, OpenAI, or LangSmith secrets in Streamlit for this project. Streamlit only needs the backend API URL.

Deploy the app.

The final Streamlit URL will look like:

```text
https://your-app-name.streamlit.app
```

---

## Step 5: Run The Demo Flow

Open the Streamlit app and test this exact flow:

1. Register a user.
2. Login.
3. Create a workspace.
4. Add a workspace member if needed.
5. Create a prompt.
6. Edit the prompt to create a new version.
7. Run evaluation.
8. Run A/B test.
9. Submit review or approval.
10. Move approved prompt to production.
11. Open analytics.
12. Check workspace activity feed.

Expected result:

```text
Prompt data appears in Postgres.
Prompt embeddings are stored in Qdrant.
Evaluations run from backend APIs.
Analytics update from backend data.
Workspace activity shows recent events.
```

---

## What Goes Where

### GitHub

GitHub should contain:

```text
source code
Dockerfiles
docker-compose.yml
README files
.env.example
requirements.txt
```

GitHub should not contain:

```text
real API keys
real database URLs
real Qdrant keys
real production secrets
local .env
private scripts
```

### Render

Render gets backend secrets:

```text
DATABASE_URL
SECRET_KEY
QDRANT_URL
QDRANT_API_KEY
OPENAI_API_KEY optional
LANGCHAIN_API_KEY optional
```

### Streamlit Cloud

Streamlit gets only:

```toml
PROMPTFORGE_API_URL = "https://your-render-backend-url.onrender.com"
```

### Neon

Neon stores:

```text
PostgreSQL database
Prompt records
Prompt versions
Users
Workspaces
Activity logs
Evaluations
A/B test results
Analytics rows
```

### Qdrant

Qdrant stores:

```text
Prompt embeddings
Semantic search vectors
Vector payload metadata
```

---

## What To Edit In Code

Usually, do not edit code during deployment.

Only update code if one of these is missing:

### `app/core/config.py`

Must include:

```python
QDRANT_URL: str = ""
QDRANT_API_KEY: str = ""
QDRANT_HOST: str = "localhost"
QDRANT_PORT: int = 6333
QDRANT_COLLECTION: str = "prompts"
```

### `app/services/vector_service.py`

Must connect to Qdrant Cloud when `QDRANT_URL` exists:

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

### `frontend/api/client.py`

Must read the backend URL from:

```python
os.getenv("PROMPTFORGE_API_URL", "http://localhost:8000")
```

This lets local development use localhost and deployed Streamlit use Render.

---

## Troubleshooting

### Streamlit login does not work

Check Streamlit secrets:

```toml
PROMPTFORGE_API_URL = "https://your-render-backend-url.onrender.com"
```

Then restart or redeploy the Streamlit app.

### Streamlit says "Error installing requirements"

Check that this file exists in the GitHub repo root:

```text
runtime.txt
```

It should contain:

```text
python-3.11
```

Then redeploy the Streamlit app from `Manage app`.

### Render backend is slow on first request

Free Render services can sleep. First request can take time.

Explain to students:

```text
Free hosting is good for demos. Production systems need always-on paid services.
```

### Backend cannot connect to Neon

Check Render environment variable:

```text
DATABASE_URL
```

It must include:

```text
sslmode=require
```

### Backend cannot connect to Qdrant

Check Render environment variables:

```text
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION
EMBEDDING_DIM
```

Also confirm that `QDRANT_URL` is the cluster API URL, not the Qdrant dashboard URL.

### Render deploy says port problem

Make sure Render has:

```text
PORT=8000
```

The backend Dockerfile exposes and runs FastAPI on port `8000`.

### Analytics is empty

Run real flows first:

```text
create prompt
run evaluation
run A/B test
approve prompt
add feedback
```

Analytics needs stored backend events before it can show useful numbers.

---

## Student Explanation Script

Use this flow while teaching:

1. "First, we separate storage from compute."
2. "Neon is our production Postgres database."
3. "Qdrant Cloud is our production vector database."
4. "Render runs the backend API."
5. "Streamlit Cloud runs only the UI."
6. "The UI calls the backend using `PROMPTFORGE_API_URL`."
7. "The backend uses `DATABASE_URL` for Postgres."
8. "The backend uses `QDRANT_URL` and `QDRANT_API_KEY` for vector search."
9. "Secrets are not code. Secrets live in hosting dashboards."
10. "The final platform is a connected AI system, not a single script."

---

## Official References

- Neon connection strings: https://neon.com/docs/get-started/connect-neon
- Qdrant Cloud quickstart: https://qdrant.tech/documentation/cloud/quickstart-cloud/
- Render deploys: https://render.com/docs/deploys
- Render environment variables: https://render.com/docs/environment-variables
- Streamlit Community Cloud deploy: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Streamlit secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
