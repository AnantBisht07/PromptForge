from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.db.models import Prompt, PromptVersion
from app.schemas.prompt_schema import PromptCreateRequest
from app.services.vector_service import create_embedding, store_vector


def create_prompt(
    request: PromptCreateRequest,
    user_id: int,
    tenant_id: str,
    session: Session,
) -> Prompt:
    """
    Full prompt creation pipeline:
    1. Save prompt to PostgreSQL
    2. Record version 1
    3. Generate embedding
    4. Store vector in Qdrant
    """
    # Step 1: persist the prompt
    # MULTI-TENANT: tenant_id is stamped onto every prompt so future queries
    # can filter by it without joining back to the User table.
    prompt = Prompt(
        content=request.content,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    session.add(prompt)
    session.commit()
    session.refresh(prompt)  # get the auto-assigned id

    # Step 2: record version 1 — every prompt starts here
    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content=prompt.content,
    )
    session.add(version)
    session.commit()

    # Step 3 & 4: embed and store in Qdrant
    # This is done after the DB commit so we have a stable prompt.id to use as the Qdrant point id
    embedding = create_embedding(prompt.content)
    store_vector(prompt_id=prompt.id, tenant_id=tenant_id, embedding=embedding)

    # Refresh to load the versions relationship for the response
    session.refresh(prompt)
    return prompt


def list_prompts(tenant_id: str, session: Session) -> list:
    """
    Return all prompts belonging to a specific tenant.

    MULTI-TENANT RULE:
    Always filter by tenant_id. Never return all prompts — that would
    expose one tenant's data to another.
    """
    return session.exec(
        select(Prompt).where(Prompt.tenant_id == tenant_id)
    ).all()


def get_prompt_versions(prompt_id: int, tenant_id: str, session: Session) -> list:
    """
    Return the full version history of a prompt.

    Security: we verify tenant_id ownership before returning versions.
    A user from a different tenant cannot read versions of another tenant's prompt.
    """
    prompt = session.exec(
        select(Prompt).where(
            Prompt.id == prompt_id,
            Prompt.tenant_id == tenant_id,  # ownership check
        )
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found or you don't have access to it.",
        )

    return session.exec(
        select(PromptVersion)
        .where(PromptVersion.prompt_id == prompt_id)
        .order_by(PromptVersion.version_number)
    ).all()
