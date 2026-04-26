# PromptForge — Multi-Tenant Prompt Management API

> A production-structured FastAPI backend built for learning how real backend systems are designed.  
> Week 25 of the AI & Full Stack Engineering Program.

---

## What Is This?

PromptForge is a backend API that lets teams store, version, and search AI prompts — the same kind of system that companies like OpenAI, Anthropic, or any AI startup would build internally.

But more importantly, it's a **learning project designed to teach you how production backends actually work** — not just how to write endpoints, but how to think about authentication, data isolation, search, and system design.

---

## What You Will Learn

| Concept | What You'll Build |
|---|---|
| **JWT Authentication** | Register/login system with signed tokens |
| **Multi-Tenancy** | Data isolation so users never see each other's data |
| **Role-Based Access Control** | Admins, Developers, Reviewers with different permissions |
| **Database Design** | Relational models with versioning built-in |
| **Vector Search** | Semantic prompt search using Qdrant |
| **Modular Architecture** | Separation of routers, services, schemas, and models |

---

## The Problem It Solves

Imagine you're building an AI product. Your team writes hundreds of prompts — for summarization, classification, code generation, etc. You need to:

- Track **who wrote which prompt**
- Keep a **version history** when prompts change
- Make sure **Company A's prompts are never visible to Company B** (multi-tenancy)
- Let users **search prompts semantically** — "find me prompts similar to this one"

That's exactly what PromptForge does.

---

## Architecture

```
Request comes in
      │
      ▼
  Router          ← handles HTTP (what URL, what method, what status code)
      │
      ▼
  Service         ← handles business logic (what actually happens)
      │
    ┌─┴─────────────┐
    ▼               ▼
  Database       Qdrant
(PostgreSQL)  (Vector DB)
```

Every layer has a single job. Routers don't touch the database directly. Services don't know about HTTP. This is called **separation of concerns** — it makes code easier to test, change, and understand.

---

## Project Structure

```
PromptForge/
├── .env.example               ← Config template — copy to .env
├── requirements.txt           ← Python dependencies
└── app/
    ├── main.py                ← App entry point, router registration
    │
    ├── core/
    │   ├── config.py          ← All settings (SECRET_KEY, DB URL, Qdrant host)
    │   └── security.py        ← JWT creation, password hashing, RBAC dependency
    │
    ├── db/
    │   ├── database.py        ← DB engine, session dependency, table creation
    │   └── models.py          ← User, Prompt, PromptVersion SQLModel tables
    │
    ├── schemas/
    │   ├── auth_schema.py     ← Request/response shapes for auth routes
    │   ├── user_schema.py     ← UserResponse (no password exposed)
    │   └── prompt_schema.py   ← Prompt create, list, version, search shapes
    │
    ├── services/
    │   ├── auth_service.py    ← register_user, login_user logic
    │   ├── prompt_service.py  ← create_prompt, list, versioning logic
    │   └── vector_service.py  ← Qdrant client, embedding, search
    │
    └── routers/
        ├── auth_router.py     ← POST /auth/register, POST /auth/login
        ├── user_router.py     ← GET /users/me, /admin-only
        └── prompt_router.py   ← POST /prompts/create, GET /list, POST /search
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **FastAPI** | Web framework — fast, async, auto-generates docs |
| **SQLModel** | Database ORM — combines SQLAlchemy + Pydantic |
| **SQLite / PostgreSQL** | Relational database for users, prompts, versions |
| **Qdrant** | Vector database for semantic search |
| **python-jose** | JWT creation and verification |
| **passlib / bcrypt** | Password hashing |
| **pydantic-settings** | Environment variable management |

---

## API Endpoints

### Authentication
| Method | URL | Who Can Use | What It Does |
|---|---|---|---|
| POST | `/auth/register` | Anyone | Create account, get tenant_id assigned |
| POST | `/auth/login` | Registered users | Get JWT token |

### Users
| Method | URL | Who Can Use | What It Does |
|---|---|---|---|
| GET | `/users/me` | Any logged-in user | See your own identity from JWT |
| GET | `/users/admin-only` | Admin only | Example RBAC-protected route |
| GET | `/users/reviewer-or-admin` | Admin + Reviewer | Example multi-role route |

### Prompts
| Method | URL | Who Can Use | What It Does |
|---|---|---|---|
| POST | `/prompts/create` | Admin, Developer | Create prompt → saves to DB + Qdrant |
| GET | `/prompts/list` | Any logged-in user | List prompts (tenant-scoped) |
| GET | `/prompts/{id}/versions` | Any logged-in user | View version history of a prompt |
| POST | `/prompts/search` | Any logged-in user | Semantic search via Qdrant |

---

## Database Schema

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│      User        │       │     Prompt        │       │   PromptVersion      │
├──────────────────┤       ├──────────────────┤       ├──────────────────────┤
│ id (PK)          │──────▶│ id (PK)          │──────▶│ id (PK)              │
│ username         │       │ content          │       │ prompt_id (FK)       │
│ hashed_password  │       │ user_id (FK)     │       │ version_number       │
│ role             │       │ tenant_id ◀────┐ │       │ content              │
│ tenant_id ───────────────│ tenant_id      │ │       │ created_at           │
└──────────────────┘       │ created_at     │ └──────────────────────────────┘
                           └────────────────┘
```

`tenant_id` is **copied from User onto Prompt** so filtering by tenant never requires a JOIN.

---

## Key Concepts Explained

### 1. JWT Authentication
After login, the server gives you a **signed token** containing:
```json
{
  "user_id": 1,
  "tenant_id": "uuid-here",
  "role": "developer",
  "exp": 1234567890
}
```
Every protected route reads this token — no database lookup needed on each request.

### 2. Multi-Tenancy
Every query that returns data is filtered by `tenant_id`:
```python
select(Prompt).where(Prompt.tenant_id == current_user["tenant_id"])
```
This is the **single most important rule** in a multi-tenant system. Without it, User A could read User B's data.

### 3. Role-Based Access Control (RBAC)
```
admin      → can do everything
developer  → can create and view prompts
reviewer   → can only view and approve
```
Enforced via a **dependency factory** — `require_role(["admin", "developer"])` — which FastAPI injects into routes automatically.

### 4. Versioning
Every prompt starts at `version_number = 1`. When a prompt is edited, a new `PromptVersion` row is created. The original is never deleted — you always have the full history.

### 5. Vector Search (Qdrant)
When a prompt is saved, it's also converted to a **vector embedding** (a list of 384 numbers that represent its meaning) and stored in Qdrant. When you search, your query is also embedded and Qdrant finds the most similar vectors.

> **Note:** This project uses a **mock embedding** for learning. To make search semantically accurate, swap `create_embedding()` in `vector_service.py` with OpenAI or sentence-transformers.

---

## How to Run

### Step 1 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Start Qdrant (Vector Database)
```bash
# Requires Docker
docker run -p 6333:6333 qdrant/qdrant
```

### Step 3 — Configure Environment
```bash
cp .env.example .env
# Edit .env and set your SECRET_KEY
```

### Step 4 — Start the API
```bash
uvicorn app.main:app --reload
```

### Step 5 — Open the Docs
```
http://localhost:8000/docs
```
FastAPI auto-generates an interactive UI where you can test every endpoint.

---

## Test Flow (Step by Step)

```bash
# 1. Register a developer
POST /auth/register
{ "username": "alice", "password": "pass123", "role": "developer" }

# 2. Login and copy the token
POST /auth/login
{ "username": "alice", "password": "pass123" }
→ returns: { "access_token": "eyJ..." }

# 3. Set Authorization: Bearer eyJ... in all further requests

# 4. Create a prompt
POST /prompts/create
{ "content": "Explain transformer architecture to a 10 year old" }

# 5. List your prompts
GET /prompts/list

# 6. Search semantically
POST /prompts/search
{ "query": "explain AI concepts simply" }

# 7. View version history
GET /prompts/1/versions
```

---

## Upgrading to Real Embeddings

In `app/services/vector_service.py`, replace `create_embedding()` with:

**Option A — OpenAI:**
```python
import openai
def create_embedding(text: str) -> list:
    response = openai.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding
```

**Option B — Free & Local (sentence-transformers):**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, matches EMBEDDING_DIM

def create_embedding(text: str) -> list:
    return model.encode(text).tolist()
```

---

## Upgrading to PostgreSQL

In `.env`, change:
```
DATABASE_URL=postgresql://username:password@localhost:5432/promptforge
```
Install the driver:
```bash
pip install psycopg2-binary
```
Everything else stays the same — SQLModel handles the rest.

---

## What's Next (Ideas to Extend)

- [ ] Add `PUT /prompts/{id}` to update a prompt and auto-increment version
- [ ] Add email field to User and send a welcome email on registration
- [ ] Add rate limiting per tenant
- [ ] Add pagination to `GET /prompts/list`
- [ ] Replace mock embeddings with a real model
- [ ] Add a `GET /prompts/search/history` to track past searches
