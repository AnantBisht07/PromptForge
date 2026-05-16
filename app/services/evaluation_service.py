import time

from sqlmodel import Session

from app.db.models import EvaluationRun
from app.evaluation.graph import graph


def run_evaluation(
    prompt: str,
    workspace_id: int,
    user_id: int,
    session: Session,
    prompt_id: int | None = None,
    source: str = "evaluate",
) -> EvaluationRun:
    """
    Run the existing LangGraph pipeline and persist a local analytics record.

    LangGraph/LangSmith remain responsible for execution and tracing. The
    EvaluationRun row supports dashboard metrics and workspace history.
    """
    started = time.perf_counter()
    result = graph.invoke({"prompt": prompt})
    latency_ms = (time.perf_counter() - started) * 1000

    run = EvaluationRun(
        workspace_id=workspace_id,
        user_id=user_id,
        prompt_id=prompt_id,
        source=source,
        prompt=result["prompt"],
        output=result["output"],
        score=float(result["score"]),
        latency_ms=round(latency_ms, 1),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
