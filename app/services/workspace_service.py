from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models import ActivityLog, Prompt, User, Workspace, WorkspaceMember
from app.schemas.workspace_schema import (
    WORKSPACE_ROLES,
    WorkspaceMemberAddRequest,
)

PROMPT_STATUSES = {"draft", "review", "approved", "production"}


def validate_prompt_status(value: str) -> str:
    if value not in PROMPT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt status must be one of: {sorted(PROMPT_STATUSES)}",
        )
    return value


def _user_id(current_user: dict) -> int:
    return int(current_user["user_id"])


def create_personal_workspace(user: User, session: Session) -> Workspace:
    """
    Backfill a workspace for users created before collaboration existed.

    New registrations also call this so every user starts in a workspace.
    """
    workspace = Workspace(
        name=f"{user.username}'s Workspace",
        owner_id=user.id,
    )
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="admin",
    )
    session.add(member)
    session.commit()
    return workspace


def get_current_workspace(current_user: dict, session: Session) -> Workspace:
    """
    Resolve the user's active workspace.

    This teaching project keeps workspace selection simple: the newest
    membership is treated as the current workspace. That lets newly-created
    or newly-added workspaces become active without adding a switch endpoint.
    """
    user_id = _user_id(current_user)
    membership = session.exec(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(WorkspaceMember.id.desc())
    ).first()

    if membership:
        workspace = session.get(Workspace, membership.workspace_id)
        if workspace:
            return workspace

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return create_personal_workspace(user, session)


def get_current_workspace_id(current_user: dict, session: Session) -> int:
    return get_current_workspace(current_user, session).id


def _membership_for(
    workspace_id: int,
    user_id: int,
    session: Session,
) -> WorkspaceMember | None:
    return session.exec(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    ).first()


def ensure_workspace_member(
    workspace_id: int,
    current_user: dict,
    session: Session,
) -> WorkspaceMember:
    member = _membership_for(workspace_id, _user_id(current_user), session)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )
    return member


def ensure_workspace_role(
    workspace_id: int,
    current_user: dict,
    allowed_roles: set[str],
    session: Session,
) -> WorkspaceMember:
    member = ensure_workspace_member(workspace_id, current_user, session)
    workspace = session.get(Workspace, workspace_id)
    if workspace and workspace.owner_id == _user_id(current_user):
        return member
    if member.role == "admin" or member.role in allowed_roles:
        return member
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Workspace role '{member.role}' cannot perform this action.",
    )


def create_workspace(
    name: str,
    current_user: dict,
    session: Session,
) -> Workspace:
    user_id = _user_id(current_user)
    workspace = Workspace(name=name, owner_id=user_id)
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role="admin",
    )
    session.add(member)
    session.commit()

    from app.services.activity_service import log_activity

    log_activity(
        workspace_id=workspace.id,
        user_id=user_id,
        event=f"Workspace '{workspace.name}' created",
        session=session,
    )
    return workspace


def add_workspace_member(
    request: WorkspaceMemberAddRequest,
    current_user: dict,
    session: Session,
) -> dict:
    workspace_id = request.workspace_id or get_current_workspace_id(current_user, session)
    ensure_workspace_role(workspace_id, current_user, {"admin"}, session)

    if request.role not in WORKSPACE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {sorted(WORKSPACE_ROLES)}",
        )

    if request.user_id is not None:
        user = session.get(User, request.user_id)
    else:
        user = session.exec(
            select(User).where(User.username == request.username)
        ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User to add was not found.",
        )

    member = _membership_for(workspace_id, user.id, session)
    if member:
        member.role = request.role
    else:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=request.role,
        )
        session.add(member)
    session.commit()
    session.refresh(member)

    from app.services.activity_service import log_activity

    log_activity(
        workspace_id=workspace_id,
        user_id=_user_id(current_user),
        event=f"Member {user.username} added as {request.role}",
        session=session,
    )
    return {
        "id": member.id,
        "workspace_id": member.workspace_id,
        "user_id": member.user_id,
        "username": user.username,
        "role": member.role,
    }


def list_workspace_members(
    current_user: dict,
    session: Session,
) -> list[dict]:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)

    rows = session.exec(
        select(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.id)
    ).all()
    return [
        {
            "id": member.id,
            "workspace_id": member.workspace_id,
            "user_id": member.user_id,
            "username": user.username,
            "role": member.role,
        }
        for member, user in rows
    ]


def list_workspace_prompts(
    current_user: dict,
    session: Session,
) -> list[Prompt]:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    return session.exec(
        select(Prompt)
        .where(Prompt.workspace_id == workspace_id)
        .order_by(Prompt.created_at.desc())
    ).all()


def get_workspace_prompt(
    prompt_id: int,
    current_user: dict,
    session: Session,
) -> Prompt:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    prompt = session.exec(
        select(Prompt).where(
            Prompt.id == prompt_id,
            Prompt.workspace_id == workspace_id,
        )
    ).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found in this workspace.",
        )
    return prompt


def set_prompt_status(
    prompt_id: int,
    new_status: str,
    current_user: dict,
    session: Session,
    comment: str = "",
) -> Prompt:
    new_status = validate_prompt_status(new_status)
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_role(workspace_id, current_user, {"reviewer"}, session)

    prompt = get_workspace_prompt(prompt_id, current_user, session)
    prompt.status = new_status
    session.add(prompt)
    session.commit()
    session.refresh(prompt)

    if new_status == "production":
        action = "approved for production"
    elif new_status == "draft":
        action = "rejected to draft"
    else:
        action = f"moved to {new_status}"
    event = f"Prompt #{prompt.id} {action}"
    if comment:
        event = f"{event}: {comment}"

    from app.services.activity_service import log_activity

    log_activity(
        workspace_id=workspace_id,
        user_id=_user_id(current_user),
        event=event,
        session=session,
    )
    return prompt


def workspace_analytics(
    current_user: dict,
    session: Session,
) -> dict:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    since = datetime.utcnow() - timedelta(hours=24)

    def count_prompts(status_value: str | None = None) -> int:
        query = select(func.count(Prompt.id)).where(Prompt.workspace_id == workspace_id)
        if status_value:
            query = query.where(Prompt.status == status_value)
        return session.exec(query).one()

    total_members = session.exec(
        select(func.count(WorkspaceMember.id)).where(
            WorkspaceMember.workspace_id == workspace_id
        )
    ).one()
    recent_activity_count = session.exec(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.workspace_id == workspace_id,
            ActivityLog.created_at >= since,
        )
    ).one()

    return {
        "workspace_id": workspace_id,
        "total_members": total_members,
        "total_prompts": count_prompts(),
        "review_queue": count_prompts("review"),
        "production_prompts": count_prompts("production"),
        "draft_prompts": count_prompts("draft"),
        "recent_activity_count": recent_activity_count,
    }
