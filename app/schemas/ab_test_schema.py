from datetime import datetime

from pydantic import BaseModel, Field


class ABTestRequest(BaseModel):
    prompt_id: int
    version_a: int
    version_b: int
    test_input: str
    rounds: int = Field(default=5, ge=1, le=20)


class ABTestEvaluation(BaseModel):
    round: int
    side: str
    prompt: str
    output: str
    score: float
    latency_ms: float


class ABTestResponse(BaseModel):
    id: int
    prompt_id: int
    version_a: int
    version_b: int
    rounds: int
    avg_score_a: float
    avg_score_b: float
    winner: str
    created_at: datetime
    evaluations: list[ABTestEvaluation]
