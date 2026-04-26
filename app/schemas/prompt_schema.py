from pydantic import BaseModel
from datetime import datetime
from typing import List


class PromptCreateRequest(BaseModel):
    content: str


class PromptVersionResponse(BaseModel):
    version_number: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptResponse(BaseModel):
    id: int
    content: str
    tenant_id: str
    created_at: datetime
    versions: List[PromptVersionResponse] = []

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str


class SearchResult(BaseModel):
    """
    A single result from the Qdrant vector search.
    score is the cosine similarity (0 to 1, higher = more similar).
    """
    prompt_id: str
    score: float
    content: str = ""
