from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List

from app.core.security import get_current_user
from app.db.database import get_session
from app.schemas.prompt_schema import (
    PromptCreateRequest,
    PromptDecisionRequest,
    PromptResponse,
    PromptUpdateRequest,
    PromptVersionResponse,
    SearchRequest,
    SearchResult,
)
from app.services.prompt_service import (
    create_prompt,
    get_prompt_versions,
    list_prompts,
    update_prompt,
)
from app.services.vector_service import search_similar
from app.services.workspace_service import (
    ensure_workspace_member,
    ensure_workspace_role,
    get_current_workspace_id,
    set_prompt_status,
)

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.post("/create", response_model=PromptResponse, status_code=201)
def create(
    request: PromptCreateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new workspace-scoped prompt.

    Existing systems are reused:
    - PostgreSQL stores the prompt and version row
    - Qdrant stores the vector
    - activity_service records the collaboration event
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_role(workspace_id, current_user, {"developer"}, session)
    prompt = create_prompt(
        request=request,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        workspace_id=workspace_id,
        session=session,
    )
    return prompt


@router.get("/list", response_model=List[PromptResponse])
def list_all(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    List all prompts for the current user's active workspace.

    WORKSPACE ISOLATION:
    Only prompts where workspace_id = current workspace are returned.
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    return list_prompts(workspace_id=workspace_id, session=session)


@router.put("/{prompt_id}", response_model=PromptResponse)
def update(
    prompt_id: int,
    request: PromptUpdateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Update a prompt, create the next version, and send it back to review.
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_role(workspace_id, current_user, {"developer"}, session)
    return update_prompt(
        prompt_id=prompt_id,
        request=request,
        user_id=current_user["user_id"],
        workspace_id=workspace_id,
        session=session,
    )


@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
def get_versions(
    prompt_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve the full version history of a workspace prompt.
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    return get_prompt_versions(
        prompt_id=prompt_id,
        workspace_id=workspace_id,
        session=session,
    )


@router.post("/approve", response_model=PromptResponse)
def approve(
    request: PromptDecisionRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Reviewer/admin action: approve a prompt and move it to production.
    """
    return set_prompt_status(
        prompt_id=request.prompt_id,
        new_status="production",
        current_user=current_user,
        session=session,
        comment=request.comment,
    )


@router.post("/reject", response_model=PromptResponse)
def reject(
    request: PromptDecisionRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Reviewer/admin action: reject a prompt back to draft.
    """
    return set_prompt_status(
        prompt_id=request.prompt_id,
        new_status="draft",
        current_user=current_user,
        session=session,
        comment=request.comment,
    )


@router.post("/search", response_model=List[SearchResult])
def search(
    request: SearchRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Semantic similarity search powered by Qdrant.

    The vector payload still uses the historical key name tenant_id, but new
    prompts store the workspace id in that field so search stays workspace
    isolated without rebuilding the vector service.
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    results = search_similar(
        query=request.query,
        tenant_id=str(workspace_id),
    )
    return [
        SearchResult(
            prompt_id=r["prompt_id"],
            score=r["score"],
        )
        for r in results
    ]
