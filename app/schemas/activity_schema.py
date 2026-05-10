from datetime import datetime

from pydantic import BaseModel


class ActivityResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    event: str
    created_at: datetime

    model_config = {"from_attributes": True}
