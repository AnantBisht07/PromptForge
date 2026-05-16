from sqlmodel import Session, select

from app.db.models import Feedback
from app.schemas.feedback_schema import FeedbackCreateRequest
from app.services.activity_service import log_activity
from app.services.workspace_service import (
    ensure_workspace_member,
    get_current_workspace_id,
    get_workspace_prompt,
)


def create_feedback(
    request: FeedbackCreateRequest,
    current_user: dict,
    session: Session,
) -> Feedback:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    prompt = get_workspace_prompt(request.prompt_id, current_user, session)

    feedback = Feedback(
        workspace_id=workspace_id,
        prompt_id=prompt.id,
        user_id=current_user["user_id"],
        decision=request.decision,
        comment=request.comment,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)

    log_activity(
        workspace_id=workspace_id,
        user_id=current_user["user_id"],
        event=f"Feedback added to Prompt #{prompt.id}: {request.decision}",
        session=session,
    )
    return feedback


def list_feedback(current_user: dict, session: Session) -> list[Feedback]:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    return session.exec(
        select(Feedback)
        .where(Feedback.workspace_id == workspace_id)
        .order_by(Feedback.created_at.desc())
        .limit(100)
    ).all()
