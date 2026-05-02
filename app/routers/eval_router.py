from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.evaluation.graph import graph
from app.core.security import get_current_user

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

    return EvalResponse(
        prompt=result["prompt"],
        output=result["output"],
        score=result["score"],
    )
