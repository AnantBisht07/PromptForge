from datetime import datetime

from pydantic import BaseModel


class PromptUsagePoint(BaseModel):
    prompt_id: int | None
    evaluations: int
    avg_score: float


class TrendPoint(BaseModel):
    created_at: datetime
    score: float
    latency_ms: float
    source: str
    prompt_id: int | None = None


class AnalyticsResponse(BaseModel):
    workspace_id: int
    total_prompts: int
    total_evaluations: int
    total_ab_tests: int
    avg_score: float | None
    avg_latency_ms: float | None
    review_queue: int
    production_prompts: int
    draft_prompts: int
    approval_rate: float
    recent_activity_count: int
    prompt_usage: list[PromptUsagePoint]
    trends: list[TrendPoint]
