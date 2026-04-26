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
    role: str = Field(default="developer")  # admin | developer | reviewer
    tenant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # SQLModel relationship — lazy loaded, not stored in DB column
    prompts: List["Prompt"] = Relationship(back_populates="user")


class Prompt(SQLModel, table=True):
    """
    Stores a prompt along with its tenant.

    WHY we copy tenant_id here:
        Multi-tenant filtering must be fast. Instead of joining to the User
        table on every query, we denormalize tenant_id onto the Prompt so we
        can do: WHERE tenant_id = ? without a join.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    user_id: int = Field(foreign_key="user.id")
    tenant_id: str = Field(index=True)  # indexed for fast per-tenant queries
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="prompts")
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
