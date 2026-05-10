from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator


WORKSPACE_ROLES = {"admin", "developer", "reviewer", "analyst"}


class WorkspaceCreateRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMemberAddRequest(BaseModel):
    workspace_id: int | None = None
    user_id: int | None = None
    username: str | None = None
    role: str = "developer"

    @model_validator(mode="after")
    def user_reference_required(self):
        if self.user_id is None and not self.username:
            raise ValueError("Provide user_id or username.")
        return self

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v):
        if v not in WORKSPACE_ROLES:
            raise ValueError(f"Role must be one of: {WORKSPACE_ROLES}")
        return v


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    username: str | None = None
    role: str


class WorkspaceAnalyticsResponse(BaseModel):
    workspace_id: int
    total_members: int
    total_prompts: int
    review_queue: int
    production_prompts: int
    draft_prompts: int
    recent_activity_count: int
