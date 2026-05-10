# Live Walkthrough Script - PromptForge Collaboration Workflows

> **Audience:** instructor running a live coding session.
> **Goal:** students understand how collaboration, approval, activity feeds, and operational analytics sit around an existing AI platform.

---

## Session Setup

Start from the Week 27 Day 1 project. The backend already has:

- auth
- prompts
- versions
- semantic search
- LangGraph evaluation
- Streamlit dashboard
- A/B testing

Say:

> "Today we are not rebuilding the AI system. We are adding the collaboration layer that teams need around it."

Run:

```powershell
cd C:\EADP\PromptForge
python -m compileall app frontend
```

Then start the app:

```powershell
uvicorn app.main:app --reload
streamlit run frontend/dashboard.py
```

---

## Lesson Plan

| Part | Time | Build |
|---|---:|---|
| 1 | 10 min | Workspace and member models |
| 2 | 10 min | Activity log model and service |
| 3 | 15 min | Workspace service and role checks |
| 4 | 15 min | Workspace and activity routers |
| 5 | 15 min | Prompt approval workflow |
| 6 | 10 min | Evaluation activity logging |
| 7 | 20 min | Workspace Streamlit page |
| 8 | 15 min | Analytics Streamlit page |
| 9 | 10 min | End-to-end demo |

---

## Part 1 - Add Collaboration Models

Open [app/db/models.py](app/db/models.py).

Explain:

> "Before teams can collaborate, we need a shared object they collaborate inside. That is Workspace."

Add:

```python
class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

Then add `WorkspaceMember`.

Ask:

> "Why not put role directly on User?"

Expected answer: a user can be a reviewer in one workspace and a developer in another.

Then add `workspace_id` and `status` to `Prompt`.

Key line to emphasize:

```python
workspace_id: Optional[int] = Field(default=None, foreign_key="workspace.id", index=True)
```

Say:

> "From this point forward, shared prompt access is workspace-scoped."

---

## Part 2 - Add Activity Logs

Still in [app/db/models.py](app/db/models.py), add:

```python
class ActivityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    event: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

Say:

> "This is the replacement for WebSockets in this lesson. We write events, then the UI refreshes."

Create [app/services/activity_service.py](app/services/activity_service.py).

Add:

```python
def log_activity(workspace_id, user_id, event, session):
    activity = ActivityLog(workspace_id=workspace_id, user_id=user_id, event=event)
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return activity
```

Add `list_activity()` for the latest rows.

---

## Part 3 - Workspace Service

Create [app/services/workspace_service.py](app/services/workspace_service.py).

Explain the core responsibilities:

- resolve active workspace
- check membership
- check workspace role
- create workspace
- add members
- list shared prompts
- update prompt status
- compute analytics

Code the role check slowly:

```python
def ensure_workspace_role(workspace_id, current_user, allowed_roles, session):
    member = ensure_workspace_member(workspace_id, current_user, session)
    if member.role == "admin" or member.role in allowed_roles:
        return member
    raise HTTPException(status_code=403, detail="Workspace role cannot perform this action.")
```

Ask:

> "Why is this not the same as the old global role check?"

Expected answer: workspace role is contextual. A user may have different roles in different teams.

---

## Part 4 - Routers

Create [app/routers/workspace_router.py](app/routers/workspace_router.py).

Add these routes:

```text
GET  /workspace/current
POST /workspace/create
POST /workspace/add-member
GET  /workspace/members
GET  /workspace/prompts
GET  /workspace/analytics
```

Create [app/routers/activity_router.py](app/routers/activity_router.py).

Add:

```text
GET /workspace/activity
```

Open [app/main.py](app/main.py) and register both routers.

Checkpoint:

```powershell
python -m compileall app
```

---

## Part 5 - Prompt Approval Workflow

Open [app/services/prompt_service.py](app/services/prompt_service.py).

Update create prompt to include:

```python
workspace_id=workspace_id
status=status_value
```

Then log:

```python
log_activity(workspace_id, user_id, f"Prompt #{prompt.id} created", session)
```

Add `update_prompt()` so editing a prompt appends a new `PromptVersion`.

Open [app/routers/prompt_router.py](app/routers/prompt_router.py).

Add:

```text
PUT  /prompts/{prompt_id}
POST /prompts/approve
POST /prompts/reject
```

Say:

> "Developers can create drafts or review-ready prompts. Only reviewers and admins move prompts to production."

---

## Part 6 - Evaluation Activity

Open [app/routers/eval_router.py](app/routers/eval_router.py).

After:

```python
result = graph.invoke({"prompt": request.prompt})
```

Add:

```python
log_activity(
    workspace_id=workspace_id,
    user_id=current_user["user_id"],
    event="New evaluation completed",
    session=session,
)
```

Say:

> "The evaluation engine did not change. We only recorded that an important workspace event happened."

---

## Part 7 - Streamlit Workspace Page

Open [frontend/api/client.py](frontend/api/client.py).

Add client methods for:

- current workspace
- members
- prompts
- activity
- approve
- reject

Then create [frontend/views/workspace.py](frontend/views/workspace.py).

Build sections in this order:

1. Refresh controls
2. Workspace metrics
3. Create workspace
4. Add member
5. Members table
6. Shared prompts table
7. Approval queue
8. Production prompts
9. Activity feed

Show the refresh pattern:

```python
if st.button("Refresh"):
    st.rerun()

if auto_refresh:
    time.sleep(interval)
    st.rerun()
```

Say:

> "This is the live experience without sockets. It is boring infrastructure, which is often the right infrastructure."

---

## Part 8 - Analytics Page

Create [frontend/views/analytics.py](frontend/views/analytics.py).

Load:

```python
analytics = api.workspace_analytics()
prompts = api.workspace_prompts()
members = api.workspace_members()
activities = api.workspace_activity(limit=50)
```

Render:

- metrics
- prompt status chart
- role distribution chart
- evaluation score chart
- activity table

Update [frontend/dashboard.py](frontend/dashboard.py) tabs:

```python
admin     -> Workspace, Developer, Reviewer, Analytics, A/B Testing
developer -> Workspace, Developer, Analytics, A/B Testing
reviewer  -> Workspace, Reviewer, Analytics
analyst   -> Workspace, Analytics
```

---

## Part 9 - End-to-End Demo

Run:

```powershell
uvicorn app.main:app --reload
streamlit run frontend/dashboard.py
```

Demo sequence:

1. Register `alice` as admin.
2. Register `bob` as reviewer in another browser/session.
3. As Alice, add Bob to the workspace as reviewer.
4. As Alice, create a prompt.
5. As Bob, open Workspace or Reviewer and approve it.
6. As Alice, run an evaluation.
7. Open Analytics and click Refresh.
8. Show the activity feed.

Expected activity examples:

```text
Prompt #1 created
Prompt #1 approved for production
New evaluation completed
```

---

## Discussion Questions

1. Why should prompt approval be a backend rule instead of only a UI button?
2. What would break if `/workspace/prompts` forgot to filter by `workspace_id`?
3. When would WebSockets become necessary?
4. Why is `ActivityLog` append-only?
5. How would you add a workspace switcher later?

---

## Final Check

Run:

```powershell
python -m compileall app frontend
```

If time allows, open FastAPI docs and try:

```text
GET /workspace/activity
GET /workspace/analytics
```

Close with:

> "The model layer answers what exists. The service layer answers who is allowed to do what. The activity layer answers what just happened. That is the shape of collaborative AI software."
