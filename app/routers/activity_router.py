from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.schemas.activity_schema import ActivityResponse
from app.services.activity_service import list_activity
from app.services.workspace_service import ensure_workspace_member, get_current_workspace_id

router = APIRouter(prefix="/workspace", tags=["Activity"])


@router.get("/activity", response_model=list[ActivityResponse])
def workspace_activity(
    limit: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Return recent workspace events.

    Frontends can call this on manual refresh or a short polling interval.
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    return list_activity(workspace_id=workspace_id, session=session, limit=limit)
