from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.schemas.ab_test_schema import ABTestRequest, ABTestResponse
from app.services.ab_test_service import run_ab_test

router = APIRouter(prefix="/ab-test", tags=["A/B Testing"])


@router.post("", response_model=ABTestResponse, status_code=201)
def create_ab_test(
    request: ABTestRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Compare two existing prompt versions through the LangGraph pipeline.

    Each evaluation is traced by LangSmith when configured and persisted as
    analytics data for the dashboard.
    """
    return run_ab_test(request, current_user, session)
