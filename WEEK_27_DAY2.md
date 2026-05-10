# PromptForge - Week 27 Day 2: Collaboration Workflows & Operational Analytics

> **Program:** AI & Full Stack Engineering
> **Week:** 27, Day 2
> **Date:** 10 May 2026
> **Built on top of:** Week 25 multi-tenant API, Week 26 evaluation engine, Week 27 Day 1 Streamlit frontend

---

## What We Are Building This Day

PromptForge already had the core AI platform pieces:

- JWT authentication
- PostgreSQL persistence
- prompt versioning
- semantic search
- LangGraph evaluation
- LangSmith tracing
- Streamlit dashboards
- A/B testing

Today we add the collaboration layer around those systems. We do not rebuild the evaluator, vector search, auth, or dashboard foundations. Instead, we add the structures that let teams work together:

1. Multi-user workspaces
2. Workspace roles
3. Shared prompts
4. Prompt approval workflows
5. Workspace activity feeds
6. Refresh-based analytics dashboards

The important constraint: **no WebSockets**. Visibility comes from normal HTTP refreshes and polling-friendly endpoints.

---

## What You Will Learn

| Concept | What You Build |
|---|---|
| Collaborative AI systems | A `Workspace` table and shared prompt scope |
| Team roles | `WorkspaceMember` rows with admin, developer, reviewer, analyst roles |
| Approval workflows | Prompt statuses: draft, review, approved, production |
| Operational visibility | Append-only `ActivityLog` events |
| Live analytics without sockets | Manual and periodic Streamlit refreshes |
| Safe data access | Every shared prompt query filters by `workspace_id` |

---

## Architecture

```
Browser / Streamlit
        |
        v
FastAPI routers
        |
        v
Services
        |
        +-- PostgreSQL: Workspace, WorkspaceMember, Prompt, ActivityLog
        |
        +-- Qdrant: existing vector search, scoped by workspace id
        |
        +-- LangGraph: existing evaluation pipeline
```

The collaboration layer is deliberately thin. It stores team state, checks workspace roles, and records activity. The AI evaluation and search systems remain reusable services.

---

## New Backend Files

| File | What It Does |
|---|---|
| [app/routers/workspace_router.py](app/routers/workspace_router.py) | `/workspace/create`, `/workspace/add-member`, `/workspace/prompts`, `/workspace/members`, `/workspace/analytics` |
| [app/routers/activity_router.py](app/routers/activity_router.py) | `/workspace/activity` refresh endpoint |
| [app/services/workspace_service.py](app/services/workspace_service.py) | workspace resolution, role checks, member management, analytics counts |
| [app/services/activity_service.py](app/services/activity_service.py) | `log_activity()` and latest activity queries |
| [app/schemas/workspace_schema.py](app/schemas/workspace_schema.py) | workspace request/response models |
| [app/schemas/activity_schema.py](app/schemas/activity_schema.py) | activity response model |

---

## Backend Files Updated

| File | Change |
|---|---|
| [app/db/models.py](app/db/models.py) | Added `Workspace`, `WorkspaceMember`, `ActivityLog`; added `workspace_id` and `status` to `Prompt` |
| [app/db/database.py](app/db/database.py) | Added lightweight startup compatibility for existing local prompt tables |
| [app/main.py](app/main.py) | Registered workspace and activity routers |
| [app/services/auth_service.py](app/services/auth_service.py) | Creates a personal workspace for new users and includes workspace context at login |
| [app/routers/auth_router.py](app/routers/auth_router.py) | Registration response now includes `workspace_id` |
| [app/routers/user_router.py](app/routers/user_router.py) | `/users/me` returns active workspace id |
| [app/services/prompt_service.py](app/services/prompt_service.py) | Prompt create/update now use `workspace_id`, status, versioning, vectors, and activity logs |
| [app/routers/prompt_router.py](app/routers/prompt_router.py) | Added update, approve, reject, and workspace-scoped list/search/version access |
| [app/routers/eval_router.py](app/routers/eval_router.py) | Logs "New evaluation completed" after LangGraph runs |
| [app/schemas/prompt_schema.py](app/schemas/prompt_schema.py) | Added prompt status, workspace id, update request, and decision request |
| [app/schemas/auth_schema.py](app/schemas/auth_schema.py) | Added `analyst` as a valid role |
| [app/schemas/user_schema.py](app/schemas/user_schema.py) | Added `workspace_id` to user responses |

---

## Frontend Files Added or Updated

| File | What It Does |
|---|---|
| [frontend/views/workspace.py](frontend/views/workspace.py) | Members, shared prompts, approval queue, production prompts, activity feed |
| [frontend/views/analytics.py](frontend/views/analytics.py) | Refresh-based operational analytics dashboard |
| [frontend/views/analyst.py](frontend/views/analyst.py) | Compatibility wrapper for the new analytics view |
| [frontend/api/client.py](frontend/api/client.py) | Added workspace, activity, prompt update, approve, and reject calls |
| [frontend/dashboard.py](frontend/dashboard.py) | Added Workspace and Analytics tabs by role |
| [frontend/views/developer.py](frontend/views/developer.py) | Added prompt status and edit-to-new-version workflow |
| [frontend/views/reviewer.py](frontend/views/reviewer.py) | Replaced session-only decisions with persistent backend approval actions |
| [frontend/views/ab_testing.py](frontend/views/ab_testing.py) | Updated guidance now that prompt update/versioning endpoint exists |
| [frontend/utils/auth.py](frontend/utils/auth.py) | Added `analyst` to registration role options |

---

## API Endpoints Added

| Method | URL | Purpose |
|---|---|---|
| GET | `/workspace/current` | Return active workspace |
| POST | `/workspace/create` | Create a workspace |
| POST | `/workspace/add-member` | Add or update a workspace member |
| GET | `/workspace/members` | List workspace members |
| GET | `/workspace/prompts` | List shared workspace prompts |
| GET | `/workspace/activity` | Return latest activity feed events |
| GET | `/workspace/analytics` | Return operational workspace metrics |
| PUT | `/prompts/{prompt_id}` | Update prompt and create a new version |
| POST | `/prompts/approve` | Approve prompt and move it to production |
| POST | `/prompts/reject` | Reject prompt back to draft |

---

## Prompt Workflow

```
Developer creates prompt
        |
        v
status = review
        |
        v
Reviewer approves or rejects
        |
        +-- approve -> status = production
        |
        +-- reject  -> status = draft
```

Developers can create and update prompts only into `draft` or `review`. They cannot write directly to `production`. Production movement goes through the approval endpoint.

---

## Activity Feed

The activity feed is an append-only table:

```
ActivityLog
- id
- workspace_id
- user_id
- event
- created_at
```

Events are written when:

- a workspace is created
- a member is added
- a prompt is created
- a prompt is updated
- a prompt is approved
- a prompt is rejected
- an evaluation is completed

The frontend reads activity with:

```
GET /workspace/activity
```

This gives a live collaboration feel with normal HTTP refreshes.

---

## Why No WebSockets?

WebSockets are useful for true real-time collaboration, but they add:

- connection lifecycle handling
- reconnect logic
- server fan-out
- message ordering concerns
- extra infrastructure in production

For this lesson, the goal is operational visibility. Refresh-based activity is simpler, observable, and enough for dashboards.

The Streamlit views provide:

- manual refresh buttons
- optional periodic refresh
- backend activity and analytics endpoints that can be polled

---

## Data Isolation Rule

The earlier lessons used:

```python
WHERE tenant_id = current_user.tenant_id
```

The collaboration layer uses:

```python
WHERE workspace_id = current_user.workspace_id
```

In this codebase, the active workspace is resolved from the user's latest workspace membership. Prompt create, list, update, versions, approval, and workspace prompt APIs all apply the workspace filter.

---

## How To Try It

Start the backend:

```powershell
uvicorn app.main:app --reload
```

Start the frontend:

```powershell
streamlit run frontend/dashboard.py
```

Suggested flow:

1. Register an admin or developer.
2. Create a prompt in the Developer tab.
3. Edit the prompt once to create version 2.
4. Open Workspace or Reviewer and approve it.
5. Run an evaluation from Developer or A/B Testing.
6. Open Analytics and click Refresh.
7. Check the activity feed.

---

## Key Takeaway

AI platforms are not only model calls and prompt storage. Real teams need shared spaces, roles, review gates, activity trails, and operational dashboards. This lesson adds those collaboration workflows while preserving the existing AI, auth, versioning, search, and evaluation systems.
