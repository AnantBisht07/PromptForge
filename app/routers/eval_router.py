from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.database import get_session
from app.services.activity_service import log_activity
from app.services.evaluation_service import run_evaluation
from app.services.workspace_service import (
    ensure_workspace_member,
    get_current_workspace_id,
    get_workspace_prompt,
)

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])


class EvalRequest(BaseModel):
    prompt: str
    prompt_id: int | None = None


class EvalResponse(BaseModel):
    prompt: str
    output: str
    score: float
    latency_ms: float


@router.post("", response_model=EvalResponse, status_code=200)
def evaluate_prompt(
    request: EvalRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Evaluate a prompt through the full LangGraph pipeline.

    Pipeline steps:
      1. **llm_node**     — sends the prompt to the LLM and stores the output
      2. **scoring_node** — scores the output for relevance (1.0–10.0)

    If LangSmith is configured (LANGCHAIN_API_KEY in .env) the entire run —
    inputs, intermediate state, outputs, and timing — is logged automatically
    to your LangSmith project.  Open https://smith.langchain.com to inspect it.

    Returns:
        prompt – the original prompt
        output – the LLM-generated response
        score  – relevance score between 1.0 and 10.0
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    if request.prompt_id is not None:
        get_workspace_prompt(request.prompt_id, current_user, session)

    result = run_evaluation(
        prompt=request.prompt,
        workspace_id=workspace_id,
        user_id=current_user["user_id"],
        prompt_id=request.prompt_id,
        source="evaluate",
        session=session,
    )
    log_activity(
        workspace_id=workspace_id,
        user_id=current_user["user_id"],
        event=(
            f"New evaluation completed for Prompt #{request.prompt_id}"
            if request.prompt_id is not None
            else "New evaluation completed"
        ),
        session=session,
    )

    return EvalResponse(
        prompt=result.prompt,
        output=result.output,
        score=result.score,
        latency_ms=result.latency_ms,
    )
