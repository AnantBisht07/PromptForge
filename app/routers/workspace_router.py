from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.schemas.prompt_schema import PromptResponse
from app.schemas.workspace_schema import (
    WorkspaceAnalyticsResponse,
    WorkspaceCreateRequest,
    WorkspaceMemberAddRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from app.services.workspace_service import (
    add_workspace_member,
    create_workspace,
    get_current_workspace,
    list_workspace_members,
    list_workspace_prompts,
    workspace_analytics,
)

router = APIRouter(prefix="/workspace", tags=["Workspace"])


@router.get("/current", response_model=WorkspaceResponse)
def current_workspace(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Return the user's active workspace."""
    return get_current_workspace(current_user, session)


@router.post("/create", response_model=WorkspaceResponse, status_code=201)
def create(
    request: WorkspaceCreateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Create a workspace and make the creator an admin member."""
    return create_workspace(request.name, current_user, session)


@router.post("/add-member", response_model=WorkspaceMemberResponse)
def add_member(
    request: WorkspaceMemberAddRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Add a user to a workspace or update their workspace role."""
    return add_workspace_member(request, current_user, session)


@router.get("/members", response_model=list[WorkspaceMemberResponse])
def members(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Return members of the active workspace."""
    return list_workspace_members(current_user, session)


@router.get("/prompts", response_model=list[PromptResponse])
def shared_prompts(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Return shared prompts in the active workspace."""
    return list_workspace_prompts(current_user, session)


@router.get("/analytics", response_model=WorkspaceAnalyticsResponse)
def analytics(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Return operational metrics for the active workspace."""
    return workspace_analytics(current_user, session)
