from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.schemas.analytics_schema import AnalyticsResponse
from app.services.analytics_service import workspace_platform_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("", response_model=AnalyticsResponse)
@router.get("/", response_model=AnalyticsResponse, include_in_schema=False)
def analytics(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Return workspace-scoped platform analytics for the dashboard."""
    return workspace_platform_analytics(current_user, session)
