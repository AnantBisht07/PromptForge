from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.evaluation.graph import graph
from app.core.security import get_current_user
from app.db.database import get_session
from app.services.activity_service import log_activity
from app.services.workspace_service import get_current_workspace_id

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])


class EvalRequest(BaseModel):
    prompt: str


class EvalResponse(BaseModel):
    prompt: str
    output: str
    score: float


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
    result = graph.invoke({"prompt": request.prompt})
    workspace_id = get_current_workspace_id(current_user, session)
    log_activity(
        workspace_id=workspace_id,
        user_id=current_user["user_id"],
        event="New evaluation completed",
        session=session,
    )

    return EvalResponse(
        prompt=result["prompt"],
        output=result["output"],
        score=result["score"],
    )
