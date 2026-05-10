from sqlmodel import Session, select

from app.db.models import ActivityLog


def log_activity(
    workspace_id: int,
    user_id: int,
    event: str,
    session: Session,
) -> ActivityLog:
    """
    Append an event to the workspace activity feed.

    This is intentionally simple: the UI gets a live-ish experience by
    refreshing or polling this table instead of opening WebSockets.
    """
    activity = ActivityLog(
        workspace_id=workspace_id,
        user_id=user_id,
        event=event,
    )
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return activity


def list_activity(
    workspace_id: int,
    session: Session,
    limit: int = 25,
) -> list[ActivityLog]:
    """Return the latest events for one workspace only."""
    return session.exec(
        select(ActivityLog)
        .where(ActivityLog.workspace_id == workspace_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    ).all()
