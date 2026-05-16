from datetime import datetime

from pydantic import BaseModel


class FeedbackCreateRequest(BaseModel):
    prompt_id: int
    decision: str = "comment"
    comment: str = ""


class FeedbackResponse(BaseModel):
    id: int
    workspace_id: int
    prompt_id: int
    user_id: int
    decision: str
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}
