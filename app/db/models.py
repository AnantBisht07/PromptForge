from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
import uuid


class User(SQLModel, table=True):
    """
    Represents a registered user.
    Each user belongs to exactly one tenant (identified by tenant_id).

    In a real SaaS product, multiple users would share the same tenant_id
    (e.g., everyone at the same company). Here, for simplicity, each new
    user gets their own unique tenant_id on registration.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="developer")  # admin | developer | reviewer | analyst
    tenant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # SQLModel relationship — lazy loaded, not stored in DB column
    prompts: List["Prompt"] = Relationship(back_populates="user")


class Workspace(SQLModel, table=True):
    """
    A shared collaboration area for prompts, reviews, and analytics.

    Workspaces sit above prompts. Users can be members of the same workspace
    even when they were originally registered under different tenant_ids.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    prompts: List["Prompt"] = Relationship(back_populates="workspace")


class WorkspaceMember(SQLModel, table=True):
    """
    Role assignment for a user inside a workspace.

    Roles:
        admin     - manage workspace and members
        developer - create/update prompts
        reviewer  - approve/reject prompts
        analyst   - read activity and analytics
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="developer")


class Prompt(SQLModel, table=True):
    """
    Stores a prompt along with its tenant and workspace.

    WHY we copy tenant_id here:
        Multi-tenant filtering must be fast. Instead of joining to the User
        table on every query, we denormalize tenant_id onto the Prompt so we
        can do: WHERE tenant_id = ? without a join.

    Collaboration note:
        New shared prompt queries filter by workspace_id. tenant_id stays for
        backwards compatibility with the earlier lessons.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    user_id: int = Field(foreign_key="user.id")
    tenant_id: str = Field(index=True)  # indexed for fast per-tenant queries
    workspace_id: Optional[int] = Field(default=None, foreign_key="workspace.id", index=True)
    status: str = Field(default="review", index=True)  # draft | review | approved | production
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="prompts")
    workspace: Optional[Workspace] = Relationship(back_populates="prompts")
    versions: List["PromptVersion"] = Relationship(back_populates="prompt")


class PromptVersion(SQLModel, table=True):
    """
    Immutable snapshot of a prompt at a point in time.

    Each time a prompt is created or updated, a new version row is added.
    This gives a full audit trail — you can always see what a prompt looked
    like at version 1, 2, 3, etc.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id")
    version_number: int  # starts at 1, increments on each update
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    prompt: Optional[Prompt] = Relationship(back_populates="versions")


class ActivityLog(SQLModel, table=True):
    """
    Append-only workspace activity feed.

    This replaces WebSockets for the learning project: clients poll or refresh
    this table to see recent operational events.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    event: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class EvaluationRun(SQLModel, table=True):
    """
    Durable record of each evaluation request.

    LangSmith keeps the trace. This table gives the platform enough local data
    to power operational analytics in Streamlit.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    prompt_id: Optional[int] = Field(default=None, foreign_key="prompt.id", index=True)
    source: str = Field(default="evaluate", index=True)
    prompt: str
    output: str
    score: float
    latency_ms: float = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ABTestRun(SQLModel, table=True):
    """
    Summary row for a version-vs-version prompt experiment.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    prompt_id: int = Field(foreign_key="prompt.id", index=True)
    version_a: int
    version_b: int
    rounds: int
    avg_score_a: float
    avg_score_b: float
    winner: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Feedback(SQLModel, table=True):
    """
    Reviewer or operator feedback linked to a workspace prompt.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    prompt_id: int = Field(foreign_key="prompt.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    decision: str = Field(default="comment", index=True)
    comment: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
