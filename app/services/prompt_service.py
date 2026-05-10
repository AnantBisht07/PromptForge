from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.db.models import Prompt, PromptVersion
from app.schemas.prompt_schema import PromptCreateRequest, PromptUpdateRequest
from app.services.activity_service import log_activity
from app.services.vector_service import create_embedding, store_vector
from app.services.workspace_service import validate_prompt_status


def _validate_edit_status(value: str) -> str:
    value = validate_prompt_status(value)
    if value not in {"draft", "review"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt create/update status must be draft or review.",
        )
    return value


def create_prompt(
    request: PromptCreateRequest,
    user_id: int,
    tenant_id: str,
    workspace_id: int,
    session: Session,
) -> Prompt:
    """
    Full prompt creation pipeline:
    1. Save prompt to PostgreSQL
    2. Record version 1
    3. Generate embedding
    4. Store vector in Qdrant
    5. Log workspace activity
    """
    status_value = _validate_edit_status(request.status)

    # WORKSPACE: every new prompt is stamped with workspace_id so all reads can
    # do WHERE workspace_id = current workspace.
    prompt = Prompt(
        content=request.content,
        user_id=user_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        status=status_value,
    )
    session.add(prompt)
    session.commit()
    session.refresh(prompt)

    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content=prompt.content,
    )
    session.add(version)
    session.commit()

    embedding = create_embedding(prompt.content)
    store_vector(prompt_id=prompt.id, tenant_id=str(workspace_id), embedding=embedding)

    log_activity(
        workspace_id=workspace_id,
        user_id=user_id,
        event=f"Prompt #{prompt.id} created",
        session=session,
    )

    session.refresh(prompt)
    return prompt


def list_prompts(workspace_id: int, session: Session) -> list:
    """
    Return all prompts belonging to a specific workspace.

    WORKSPACE RULE:
    Always filter by workspace_id. Never return all prompts because that would
    expose one workspace's assets to another.
    """
    return session.exec(
        select(Prompt)
        .where(Prompt.workspace_id == workspace_id)
        .order_by(Prompt.created_at.desc())
    ).all()


def get_prompt_versions(prompt_id: int, workspace_id: int, session: Session) -> list:
    """
    Return the full version history of a prompt.

    Security: we verify workspace ownership before returning versions.
    """
    prompt = session.exec(
        select(Prompt).where(
            Prompt.id == prompt_id,
            Prompt.workspace_id == workspace_id,
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


def update_prompt(
    prompt_id: int,
    request: PromptUpdateRequest,
    user_id: int,
    workspace_id: int,
    session: Session,
) -> Prompt:
    """
    Update a prompt and append a new immutable version.

    This extends the existing versioning system instead of replacing it.
    """
    status_value = _validate_edit_status(request.status)
    prompt = session.exec(
        select(Prompt).where(
            Prompt.id == prompt_id,
            Prompt.workspace_id == workspace_id,
        )
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found or you don't have access to it.",
        )

    latest_version = session.exec(
        select(PromptVersion)
        .where(PromptVersion.prompt_id == prompt_id)
        .order_by(PromptVersion.version_number.desc())
    ).first()
    next_version = (latest_version.version_number if latest_version else 0) + 1

    prompt.content = request.content
    prompt.status = status_value
    session.add(prompt)
    session.commit()
    session.refresh(prompt)

    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=next_version,
        content=prompt.content,
    )
    session.add(version)
    session.commit()

    embedding = create_embedding(prompt.content)
    store_vector(prompt_id=prompt.id, tenant_id=str(workspace_id), embedding=embedding)

    log_activity(
        workspace_id=workspace_id,
        user_id=user_id,
        event=f"Prompt #{prompt.id} updated to v{next_version}",
        session=session,
    )

    session.refresh(prompt)
    return prompt
