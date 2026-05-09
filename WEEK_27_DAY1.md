# PromptForge — Week 27 · Day 1: Containerization & the Streamlit Frontend Layer

> **Program:** AI & Full Stack Engineering
> **Week:** 27, Day 1
> **Date:** 9 May 2026
> **Built on top of:** Week 25 (multi-tenant API) + Week 26 (LangGraph evaluation engine)

---

## What We Are Building This Day

Last week we finished the **brains** — a LangGraph evaluation pipeline tracing through LangSmith. The backend ran on your laptop with `uvicorn` and a SQLite file.

Today we do two things at once:

1. **Containerize the platform.** One `docker compose up` brings up the API, a real PostgreSQL, and a real Qdrant — no more hand-running `pip install` and three terminal windows.
2. **Add a frontend.** A Streamlit dashboard that *consumes* the existing FastAPI without rebuilding any of its logic. Different user roles see different tabs. A/B testing is orchestrated entirely from the UI by calling `/evaluate` twice per round.

**What stays untouched:** every file inside `app/`. We did not add a single backend endpoint. The whole frontend talks to the four routers that already existed (`/auth`, `/users`, `/prompts/*`, `/evaluate`). That separation is the lesson.

---

## The Core Idea

```
┌──────────────────────────────────┐        ┌──────────────────────────┐
│  Streamlit Frontend              │        │   FastAPI Backend        │
│  (browser at :8501)              │        │   (container at :8000)   │
│                                  │        │                          │
│  ┌──────────────────────────┐    │  HTTP  │  /auth/register          │
│  │ APIClient                │────┼───────▶│  /auth/login             │
│  │  • token in session_state│    │        │  /users/me               │
│  │  • injects Bearer header │    │        │  /prompts/create         │
│  │  • measures latency      │    │        │  /prompts/list           │
│  └──────────────────────────┘    │        │  /prompts/{id}/versions  │
│                                  │        │  /prompts/search         │
│  Tabs by role:                   │        │  /evaluate               │
│   admin     → 4 tabs             │        └──────────────┬───────────┘
│   developer → 3 tabs (no Review) │                       │
│   reviewer  → 2 tabs (read-only) │                       ▼
└──────────────────────────────────┘                ┌──────────────┐
                                                    │  Postgres    │
                                                    │  Qdrant      │
                                                    └──────────────┘
                  All running under one
                   `docker compose up`.
```

Two layers. One contract (the API). The frontend is a *consumer*, not a re-implementation.

---

## What You Will Learn

| Concept | What You Will Build |
|---|---|
| **Multi-service Compose** | A `docker-compose.yml` running api + Postgres + Qdrant with a real healthcheck on the database |
| **Service-to-service DNS** | Why the api uses `db:5432` (not `localhost`) inside the network |
| **Layered Dockerfile** | Caching `pip install` separately from app code so rebuilds are seconds, not minutes |
| **Frontend/Backend separation** | A typed API client (`requests` + JWT) sitting between Streamlit and FastAPI |
| **Streamlit primitives** | `st.tabs`, `st.session_state`, `st.form`, `st.metric`, `st.line_chart`, `st.bar_chart` |
| **Role-based UI** | Mirroring backend RBAC in the frontend so users never see buttons that would 403 |
| **A/B testing as orchestration** | Comparing two versions by calling `/evaluate` twice per round — no new backend |
| **Honest UX for missing endpoints** | Banners that say "this is session-local" instead of pretending the backend has it |

---

## New Files Created

### Containerization (repo root)

| File | What It Does |
|---|---|
| [Dockerfile](Dockerfile) | Builds a `python:3.11-slim` image, installs deps, runs `uvicorn` on `:8000` |
| [docker-compose.yml](docker-compose.yml) | Defines `api`, `db` (Postgres 16-alpine), `qdrant` services, plus their volumes and the db healthcheck |
| [.dockerignore](.dockerignore) | Keeps `__pycache__`, `.env`, local `*.db` files, `.git` out of the build context |

### `frontend/` — the new Streamlit layer

| File | What It Does |
|---|---|
| [frontend/dashboard.py](frontend/dashboard.py) | App entry point. Renders sidebar login + role-based `st.tabs()` |
| [frontend/api/client.py](frontend/api/client.py) | `APIClient` — typed wrapper around `requests` with JWT injection, latency timing, and `AuthExpired` / `PermissionDenied` exceptions |
| [frontend/utils/auth.py](frontend/utils/auth.py) | `login_form`, `register_form`, `logout`, `require_auth`, session state helpers |
| [frontend/utils/charts.py](frontend/utils/charts.py) | `score_trend`, `ab_bar`, `metric_grid`, `score_histogram` chart helpers |
| [frontend/views/developer.py](frontend/views/developer.py) | Create prompts, version table, evaluate latest, score-trend chart, semantic search |
| [frontend/views/reviewer.py](frontend/views/reviewer.py) | Session-local review queue: filter by score, approve/reject/comment |
| [frontend/views/analyst.py](frontend/views/analyst.py) | Live metric tiles, top-prompts bar, score histogram, latency line |
| [frontend/views/ab_testing.py](frontend/views/ab_testing.py) | Two-version A/B compare, N rounds, winner highlight, raw-output expander |
| [frontend/.streamlit/config.toml](frontend/.streamlit/config.toml) | Dark theme polish |

> **Note on folder name:** the spec called this `pages/`, but we used `views/`. Streamlit treats a sibling `pages/` folder as **automatic multipage routing** (each file becomes a separate sidebar page). That fights the `st.tabs()` UX we want, so we renamed it.

---

## Files Updated

| File | What Changed |
|---|---|
| [requirements.txt](requirements.txt) | Added `psycopg2-binary==2.9.9` (Postgres driver) and `streamlit==1.40.0` |
| [.env.example](.env.example) | Documented the in-compose Postgres URL pattern (host = `db`) and Qdrant compose host (`qdrant`) |

> **No file inside `app/` was modified.** The whole point of this day is to add a new layer **outside** the existing system without touching it.

---

## Architecture Deep Dive

### 1. Why containerize now?

In Week 26 the README said *"Step 2 — Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`"*. That works for one service. We now have three (api, db, qdrant) and they need to talk to each other. A **Compose file** is one declaration of the entire stack — `up -d` brings everything up in the right order, `down` cleans it up, volumes survive restarts.

### 2. The healthcheck bug we explicitly avoided

A naïve compose looks like:

```yaml
api:
  depends_on:
    db:
      condition: service_healthy   # ← needs the db to declare a healthcheck
db:
  image: postgres:16-alpine        # ← but postgres has no built-in healthcheck
```

The api sits in `created` state forever waiting for a "healthy" signal that never comes. We add one explicitly:

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres -d promptforge"]
    interval: 5s
    timeout: 3s
    retries: 5
```

`pg_isready` ships with the postgres image. Now the api waits ~5–15s and starts cleanly.

### 3. Service-to-service DNS

Inside the compose network, every service is reachable at its **service name** as a hostname. So the api's environment is:

```yaml
DATABASE_URL: postgresql://postgres:password@db:5432/promptforge
QDRANT_HOST: qdrant
```

Not `localhost`. Two containers on the same compose network resolve each other via Docker's embedded DNS — `db` and `qdrant` are valid hostnames *only inside the compose network*, which is exactly what we want.

### 4. The frontend is a *consumer*

This is the structural lesson. The frontend has **zero** knowledge of:
- How the LangGraph nodes work
- How JWTs are signed
- How prompts are stored in Postgres
- How embeddings are upserted into Qdrant

It only knows the **HTTP contract**: send JSON, get JSON, attach `Authorization: Bearer <token>`. The same contract a third-party CLI, a mobile app, or a teammate's React project would target.

```python
# frontend/api/client.py — the only place that knows about endpoints
def evaluate(self, prompt: str) -> dict:
    t0 = time.perf_counter()
    body = self._request("POST", "/evaluate", json={"prompt": prompt})
    body["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
    return body
```

Every view module imports this client; **no view file ever calls `requests` directly**.

### 5. Latency: measured client-side, on purpose

The backend's `/evaluate` response is `{prompt, output, score}` — no timing. Adding timing to the backend would have meant editing `app/`, which we promised not to do. So we wrap the HTTP call in `time.perf_counter()` and add `latency_ms` to the dict before returning. That's a real measurement of *user-perceived* latency: round-trip + LangGraph + scoring + JSON serialize.

### 6. Role-based tabs — mirroring `require_role`

The backend gates with FastAPI dependencies (`Depends(require_role(["admin", "developer"]))`). If the frontend showed a "Create prompt" button to a `reviewer`, the click would 403. So the frontend mirrors the rule:

```python
TABS_BY_ROLE = {
    "admin":     [Developer, Reviewer, Analyst, AB_Testing],
    "developer": [Developer, Analyst, AB_Testing],
    "reviewer":  [Reviewer, Analyst],
}
```

A reviewer never sees the Developer tab — there's nothing they could do there. The backend is still the source of truth (we don't trust the frontend with security), but UX-wise we don't surface broken affordances.

### 7. A/B testing as client-side orchestration

The spec called for `/ab-test` on the backend. We don't have it. But we don't need it — the backend has `/evaluate` and the frontend has loops:

```python
for round_idx in range(N):
    prompt_a = version_a.content + "\n\n" + test_input
    prompt_b = version_b.content + "\n\n" + test_input
    result_a = api.evaluate(prompt_a)   # single LangGraph run
    result_b = api.evaluate(prompt_b)   # single LangGraph run
    a_scores.append(result_a["score"])
    b_scores.append(result_b["score"])
```

Win-rate, average latency, and the bar chart are all computed in the browser tab. Two HTTP calls per round. The LangGraph pipeline + LangSmith trace logs are reused as-is.

### 8. Session state — Streamlit's mental model

Streamlit re-runs the script **top to bottom on every interaction**. Without persistence between reruns, the page would forget everything you did. `st.session_state` is a per-tab dict that survives reruns:

```python
st.session_state["token"]                       # JWT after login
st.session_state["user"]                        # decoded user from /users/me
st.session_state["evaluations"] = [ … ]         # every eval done this session
st.session_state["feedback"][eval_id] = { … }   # reviewer decisions
```

When the user closes the tab, it all clears. That's why we explicitly tell reviewers their comments are session-local — the state model dictates the UX.

### 9. Honest UX for the gaps

The spec also asked for `/analytics`, `/feedback`, `/clusters`. Those endpoints don't exist. Three options:

1. Mock data with a fake "loading…" — looks complete, lies about the system.
2. Hide the tabs entirely — denies the teaching opportunity.
3. **Build the UI, label it honestly.** ← what we did.

Each unfinished area gets a banner: *"Comments are session-local. Persistence requires a `/feedback` endpoint."* The student sees what the next iteration of the platform needs to grow.

---

## Endpoints The Frontend Consumes

> All eight already existed. Nothing new.

| Endpoint | Used by |
|---|---|
| `POST /auth/register` | sidebar register form |
| `POST /auth/login` | sidebar login form |
| `GET /users/me` | every login → store role in session_state |
| `POST /prompts/create` | Developer tab → Create new prompt |
| `GET /prompts/list` | Developer + A/B + Analyst tabs |
| `GET /prompts/{id}/versions` | Developer tab table |
| `POST /prompts/search` | Developer tab → Semantic search panel |
| `POST /evaluate` | Developer (single + score-trend), A/B (N×2 calls per run) |

---

## How to Run

### Step 1 — Install deps (once)

```bash
pip install -r requirements.txt
```

### Step 2 — Start the backend stack

```bash
docker compose up -d --build
# api    → http://localhost:8000/docs
# qdrant → http://localhost:6333/dashboard  (or 6433 if your host port is taken)
```

### Step 3 — Start the frontend

```bash
streamlit run frontend/dashboard.py
# Browser opens http://localhost:8501
```

### Step 4 — Register and play

1. Click **Register**, create `dev1` with role `developer`.
2. Login → tabs appear.
3. Developer tab → **Create new prompt** → "Explain transformers in one paragraph."
4. Click **Evaluate latest version** → see score + latency.
5. Run **Score trend across versions** to see the chart populate.
6. Switch to **A/B Testing** → pick the prompt, two versions, type a shared input, run 5 rounds.
7. Watch the **Analyst** tab tiles update live.

---

## Verification Checklist

```bash
# Backend reachable
curl http://localhost:8000/

# Postgres healthy
docker compose ps              # db should be (healthy)

# Frontend reachable
curl http://localhost:8501/_stcore/health   # → ok

# All four routers respond
curl -X POST localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username":"smoke","password":"test12345","role":"developer"}'
```

The accompanying [WEEK_27_DAY1_CODE_WALKTHROUGH.md](WEEK_27_DAY1_CODE_WALKTHROUGH.md) walks through every line of every new file in the order a learner should read them.

---

## Dependency Map (Day 1 only)

```
docker compose up
    ├── api ───▶  uvicorn app.main:app  ──▶  Week 26 LangGraph + Week 25 prompts
    ├── db ────▶  postgresql://postgres:password@db:5432/promptforge
    └── qdrant ▶  http://qdrant:6333

streamlit run frontend/dashboard.py
    ├── frontend/api/client.py    ──▶  http://localhost:8000/*
    └── frontend/views/*.py       ──▶  uses APIClient only
```

---

## What's Next (Day 2 ideas)

- [ ] Add `EvaluationRun` table → persist `/evaluate` results so analytics survives a refresh
- [ ] Add `Feedback` table + `POST /feedback` → reviewer comments persist
- [ ] Add `PUT /prompts/{id}` → editing a prompt creates a real v2, v3, … (today the only way to bump version is to recreate)
- [ ] Replace mock embeddings in `vector_service.py` with `sentence-transformers/all-MiniLM-L6-v2` so search is actually meaningful
- [ ] Replace the keyword scorer with an LLM-as-judge call (GPT-4 scoring GPT-3.5's output) so A/B test runs produce non-tied results
- [ ] Embed LangSmith trace links in the Reviewer tab — one click jumps to the run trace
- [ ] CI: run a `docker compose up`-based smoke test on every PR
