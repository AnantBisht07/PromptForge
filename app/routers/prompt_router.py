from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List
from app.db.database import get_session
from app.core.security import get_current_user, require_role
from app.schemas.prompt_schema import (
    PromptCreateRequest,
    PromptResponse,
    PromptVersionResponse,
    SearchRequest,
    SearchResult,
)
from app.services.prompt_service import create_prompt, list_prompts, get_prompt_versions
from app.services.vector_service import search_similar

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.post("/create", response_model=PromptResponse, status_code=201)
def create(
    request: PromptCreateRequest,
    session: Session = Depends(get_session),
    # Role check: only admins and developers may create prompts
    current_user: dict = Depends(require_role(["admin", "developer"])),
):
    """
    Create a new prompt. Full pipeline:
    1. Auth + role check (admin/developer only)
    2. Save to PostgreSQL with tenant_id
    3. Auto-create version 1
    4. Generate embedding (mock) → store in Qdrant
    """
    prompt = create_prompt(
        request=request,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        session=session,
    )
    return prompt


@router.get("/list", response_model=List[PromptResponse])
def list_all(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),  # any authenticated user
):
    """
    List all prompts for the current user's tenant.

    MULTI-TENANT: Only prompts where tenant_id = current user's tenant_id
    are returned. Other tenants' prompts are completely invisible.
    """
    return list_prompts(tenant_id=current_user["tenant_id"], session=session)


@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
def get_versions(
    prompt_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve the full version history of a prompt.
    Only accessible if the prompt belongs to your tenant.
    """
    return get_prompt_versions(
        prompt_id=prompt_id,
        tenant_id=current_user["tenant_id"],
        session=session,
    )


@router.post("/search", response_model=List[SearchResult])
def search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Semantic similarity search powered by Qdrant.

    Flow:
    1. Convert the query string into a vector embedding
    2. Ask Qdrant for the top-5 nearest vectors
    3. Qdrant filters by tenant_id — cross-tenant results are blocked

    Note: with mock embeddings the results won't be semantically meaningful.
    Swap create_embedding() in vector_service.py for a real model to fix this.
    """
    results = search_similar(
        query=request.query,
        tenant_id=current_user["tenant_id"],
    )
    return [
        SearchResult(
            prompt_id=r["prompt_id"],
            score=r["score"],
        )
        for r in results
    ]
