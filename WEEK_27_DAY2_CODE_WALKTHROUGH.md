# Week 27 Day 2 - Code Walkthrough

> Companion to [WEEK_27_DAY2.md](WEEK_27_DAY2.md). The lesson file explains what was built. This walkthrough explains how the code is organized and why each major change exists.

---

## Reading Order

1. [app/db/models.py](app/db/models.py)
2. [app/db/database.py](app/db/database.py)
3. [app/services/activity_service.py](app/services/activity_service.py)
4. [app/services/workspace_service.py](app/services/workspace_service.py)
5. [app/services/prompt_service.py](app/services/prompt_service.py)
6. [app/routers/workspace_router.py](app/routers/workspace_router.py)
7. [app/routers/activity_router.py](app/routers/activity_router.py)
8. [app/routers/prompt_router.py](app/routers/prompt_router.py)
9. [app/routers/eval_router.py](app/routers/eval_router.py)
10. [frontend/api/client.py](frontend/api/client.py)
11. [frontend/views/workspace.py](frontend/views/workspace.py)
12. [frontend/views/analytics.py](frontend/views/analytics.py)
13. [frontend/views/developer.py](frontend/views/developer.py)
14. [frontend/views/reviewer.py](frontend/views/reviewer.py)
15. [frontend/dashboard.py](frontend/dashboard.py)

---

## 1. Models: Collaboration Tables

[app/db/models.py](app/db/models.py) gains three tables.

`Workspace` is the shared area:

```python
class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

`WorkspaceMember` maps users to workspaces:

```python
class WorkspaceMember(SQLModel, table=True):
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="developer")
```

`ActivityLog` stores operational events:

```python
class ActivityLog(SQLModel, table=True):
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    event: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

The existing `Prompt` table keeps `tenant_id`, but now also has:

```python
workspace_id: Optional[int] = Field(default=None, foreign_key="workspace.id", index=True)
status: str = Field(default="review", index=True)
```

That is the core change. Prompt access is now team-scoped.

---

## 2. Database Startup Compatibility

[app/db/database.py](app/db/database.py) still calls:

```python
SQLModel.metadata.create_all(engine)
```

But `create_all()` does not alter an existing table. If a local learner already has a `prompt` table from Week 25 or Week 26, it will not automatically receive `workspace_id` or `status`.

So Day 2 adds:

```python
_ensure_prompt_collaboration_columns()
_backfill_default_workspaces()
```

This is intentionally lightweight. It is not a full migration framework. In a production app, this job belongs to Alembic.

---

## 3. Activity Service

[app/services/activity_service.py](app/services/activity_service.py) has two functions.

```python
log_activity(workspace_id, user_id, event, session)
```

adds one row to `ActivityLog`.

```python
list_activity(workspace_id, session, limit=25)
```

returns latest events for exactly one workspace.

This is the replacement for WebSockets in the lesson. The frontend refreshes this endpoint when it wants current activity.

---

## 4. Workspace Service

[app/services/workspace_service.py](app/services/workspace_service.py) owns collaboration rules.

Important functions:

| Function | Purpose |
|---|---|
| `get_current_workspace()` | Resolve the user's active workspace |
| `ensure_workspace_member()` | Block users outside the workspace |
| `ensure_workspace_role()` | Enforce admin/developer/reviewer/analyst actions |
| `create_workspace()` | Create workspace and admin membership |
| `add_workspace_member()` | Add or update a user's workspace role |
| `list_workspace_prompts()` | Return prompts filtered by workspace |
| `set_prompt_status()` | Approve/reject prompts |
| `workspace_analytics()` | Return dashboard counts |

The active workspace rule is simple for teaching:

```python
newest WorkspaceMember row = active workspace
```

That means a newly-created workspace or a newly-added shared workspace becomes active without introducing a separate workspace switch endpoint.

---

## 5. Prompt Service

[app/services/prompt_service.py](app/services/prompt_service.py) still owns prompt persistence and versioning. Day 2 extends it instead of replacing it.

Create flow:

1. Validate status is `draft` or `review`.
2. Insert `Prompt` with `workspace_id`.
3. Insert `PromptVersion` v1.
4. Create embedding.
5. Store vector in Qdrant.
6. Log activity.

Update flow:

1. Look up prompt by `prompt_id` and `workspace_id`.
2. Update content/status.
3. Append next `PromptVersion`.
4. Upsert the vector.
5. Log activity.

The important security line is always the workspace filter:

```python
select(Prompt).where(Prompt.id == prompt_id, Prompt.workspace_id == workspace_id)
```

---

## 6. Workspace Router

[app/routers/workspace_router.py](app/routers/workspace_router.py) exposes the team API:

```text
GET  /workspace/current
POST /workspace/create
POST /workspace/add-member
GET  /workspace/members
GET  /workspace/prompts
GET  /workspace/analytics
```

The router does not contain business logic. It accepts HTTP input, calls the service, and returns response models.

---

## 7. Activity Router

[app/routers/activity_router.py](app/routers/activity_router.py) exposes:

```text
GET /workspace/activity
```

It resolves the current workspace, verifies membership, then returns `ActivityLog` rows.

---

## 8. Prompt Router

[app/routers/prompt_router.py](app/routers/prompt_router.py) now checks workspace roles:

- create/update require workspace `developer` or `admin`
- approve/reject require workspace `reviewer` or `admin`
- list/search/versions require workspace membership

New endpoints:

```text
PUT  /prompts/{prompt_id}
POST /prompts/approve
POST /prompts/reject
```

Approve moves a prompt to `production`. Reject moves it to `draft`.

---

## 9. Evaluation Router

[app/routers/eval_router.py](app/routers/eval_router.py) still invokes the existing LangGraph:

```python
result = graph.invoke({"prompt": request.prompt})
```

Day 2 adds only one collaboration side effect:

```python
log_activity(..., event="New evaluation completed")
```

The evaluation engine itself is not rebuilt.

---

## 10. API Client

[frontend/api/client.py](frontend/api/client.py) remains the single HTTP boundary for Streamlit.

New client methods include:

```python
current_workspace()
create_workspace(name)
add_member(...)
workspace_members()
workspace_prompts()
workspace_activity()
workspace_analytics()
update_prompt(...)
approve_prompt(...)
reject_prompt(...)
```

Views still import the client instead of calling `requests` directly.

---

## 11. Workspace View

[frontend/views/workspace.py](frontend/views/workspace.py) shows:

- current workspace
- member list
- shared prompt list
- approval queue
- production prompts
- recent activity

It has a manual Refresh button and optional periodic refresh:

```python
if auto_refresh:
    time.sleep(interval)
    st.rerun()
```

That is the no-WebSocket live experience.

---

## 12. Analytics View

[frontend/views/analytics.py](frontend/views/analytics.py) combines:

- backend workspace metrics
- prompt status counts
- member role distribution
- activity feed rows
- current Streamlit session evaluation scores

The backend gives durable operational counts. Session evaluation data still comes from the existing Day 1 dashboard flow.

---

## 13. Developer View

[frontend/views/developer.py](frontend/views/developer.py) now displays prompt status and includes an "Edit prompt" form.

Saving an edit calls:

```python
api.update_prompt(prompt["id"], edited_content, status="review")
```

That creates a new prompt version and returns the prompt to the approval queue.

---

## 14. Reviewer View

[frontend/views/reviewer.py](frontend/views/reviewer.py) no longer stores decisions only in `st.session_state`.

It calls:

```python
api.approve_prompt(prompt_id, comment)
api.reject_prompt(prompt_id, comment)
```

Those actions persist status changes and activity events.

---

## 15. Dashboard Wiring

[frontend/dashboard.py](frontend/dashboard.py) adds role-based tabs:

```python
admin     -> Workspace, Developer, Reviewer, Analytics, A/B Testing
developer -> Workspace, Developer, Analytics, A/B Testing
reviewer  -> Workspace, Reviewer, Analytics
analyst   -> Workspace, Analytics
```

The backend remains the source of truth for permissions. The UI only mirrors likely workflows.

---

## Verification

Syntax check:

```powershell
python -m compileall app frontend
```

Expected result: every touched backend and frontend module compiles successfully.

---

## Main Design Decision

The key design decision is to add collaboration as a layer around the existing platform:

- Auth stays JWT-based.
- Evaluation stays LangGraph-based.
- Search stays Qdrant-based.
- Versioning stays `PromptVersion`-based.
- Frontend stays Streamlit-based.

Day 2 adds team workflow and visibility without replacing the AI systems underneath.
