from statistics import mean

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.db.models import ABTestRun, Prompt, PromptVersion
from app.schemas.ab_test_schema import ABTestRequest
from app.services.activity_service import log_activity
from app.services.evaluation_service import run_evaluation
from app.services.workspace_service import (
    ensure_workspace_member,
    get_current_workspace_id,
)


def _get_version(
    prompt_id: int,
    version_number: int,
    session: Session,
) -> PromptVersion:
    version = session.exec(
        select(PromptVersion).where(
            PromptVersion.prompt_id == prompt_id,
            PromptVersion.version_number == version_number,
        )
    ).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version v{version_number} was not found.",
        )
    return version


def run_ab_test(request: ABTestRequest, current_user: dict, session: Session) -> dict:
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)

    if request.version_a == request.version_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A/B test requires two different versions.",
        )
    if not request.test_input.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="test_input cannot be empty.",
        )

    prompt = session.exec(
        select(Prompt).where(
            Prompt.id == request.prompt_id,
            Prompt.workspace_id == workspace_id,
        )
    ).first()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found in this workspace.",
        )

    version_a = _get_version(request.prompt_id, request.version_a, session)
    version_b = _get_version(request.prompt_id, request.version_b, session)
    test_input = request.test_input.strip()

    evaluations = []
    scores_a, scores_b = [], []
    for round_no in range(1, request.rounds + 1):
        run_a = run_evaluation(
            prompt=f"{version_a.content}\n\n{test_input}",
            workspace_id=workspace_id,
            user_id=current_user["user_id"],
            prompt_id=prompt.id,
            source="ab_test_A",
            session=session,
        )
        scores_a.append(run_a.score)
        evaluations.append({
            "round": round_no,
            "side": "A",
            "prompt": run_a.prompt,
            "output": run_a.output,
            "score": run_a.score,
            "latency_ms": run_a.latency_ms,
        })

        run_b = run_evaluation(
            prompt=f"{version_b.content}\n\n{test_input}",
            workspace_id=workspace_id,
            user_id=current_user["user_id"],
            prompt_id=prompt.id,
            source="ab_test_B",
            session=session,
        )
        scores_b.append(run_b.score)
        evaluations.append({
            "round": round_no,
            "side": "B",
            "prompt": run_b.prompt,
            "output": run_b.output,
            "score": run_b.score,
            "latency_ms": run_b.latency_ms,
        })

    avg_a = round(mean(scores_a), 2)
    avg_b = round(mean(scores_b), 2)
    winner = "A" if avg_a > avg_b else "B" if avg_b > avg_a else "Tie"

    ab_run = ABTestRun(
        workspace_id=workspace_id,
        user_id=current_user["user_id"],
        prompt_id=prompt.id,
        version_a=request.version_a,
        version_b=request.version_b,
        rounds=request.rounds,
        avg_score_a=avg_a,
        avg_score_b=avg_b,
        winner=winner,
    )
    session.add(ab_run)
    session.commit()
    session.refresh(ab_run)

    log_activity(
        workspace_id=workspace_id,
        user_id=current_user["user_id"],
        event=(
            f"A/B test completed for Prompt #{prompt.id}: "
            f"v{request.version_a} vs v{request.version_b}, winner {winner}"
        ),
        session=session,
    )

    return {
        "id": ab_run.id,
        "prompt_id": prompt.id,
        "version_a": request.version_a,
        "version_b": request.version_b,
        "rounds": request.rounds,
        "avg_score_a": avg_a,
        "avg_score_b": avg_b,
        "winner": winner,
        "created_at": ab_run.created_at,
        "evaluations": evaluations,
    }
