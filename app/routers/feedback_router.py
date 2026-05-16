from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.schemas.feedback_schema import FeedbackCreateRequest, FeedbackResponse
from app.services.feedback_service import create_feedback, list_feedback

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse, status_code=201)
def add_feedback(
    request: FeedbackCreateRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Add review or operator feedback to a workspace prompt."""
    return create_feedback(request, current_user, session)


@router.get("", response_model=list[FeedbackResponse])
def feedback(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Return recent feedback for the active workspace."""
    return list_feedback(current_user, session)
