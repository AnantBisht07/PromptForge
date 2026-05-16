from datetime import datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models import ABTestRun, ActivityLog, EvaluationRun, Prompt
from app.services.workspace_service import ensure_workspace_member, get_current_workspace_id


def workspace_platform_analytics(current_user: dict, session: Session) -> dict:
    """
    Aggregate operational analytics for the active workspace.

    Evaluation traces still live in LangSmith. These local aggregates are for
    the Streamlit dashboard and use workspace filters on every query.
    """
    workspace_id = get_current_workspace_id(current_user, session)
    ensure_workspace_member(workspace_id, current_user, session)
    since = datetime.utcnow() - timedelta(hours=24)

    def count_prompts(status_value: str | None = None) -> int:
        query = select(func.count(Prompt.id)).where(Prompt.workspace_id == workspace_id)
        if status_value:
            query = query.where(Prompt.status == status_value)
        return int(session.exec(query).one() or 0)

    total_prompts = count_prompts()
    production_prompts = count_prompts("production")
    review_queue = count_prompts("review")
    draft_prompts = count_prompts("draft")

    total_evaluations = int(session.exec(
        select(func.count(EvaluationRun.id)).where(
            EvaluationRun.workspace_id == workspace_id
        )
    ).one() or 0)
    total_ab_tests = int(session.exec(
        select(func.count(ABTestRun.id)).where(ABTestRun.workspace_id == workspace_id)
    ).one() or 0)
    avg_score = session.exec(
        select(func.avg(EvaluationRun.score)).where(
            EvaluationRun.workspace_id == workspace_id
        )
    ).one()
    avg_latency = session.exec(
        select(func.avg(EvaluationRun.latency_ms)).where(
            EvaluationRun.workspace_id == workspace_id
        )
    ).one()
    recent_activity_count = int(session.exec(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.workspace_id == workspace_id,
            ActivityLog.created_at >= since,
        )
    ).one() or 0)

    usage_rows = session.exec(
        select(
            EvaluationRun.prompt_id,
            func.count(EvaluationRun.id),
            func.avg(EvaluationRun.score),
        )
        .where(EvaluationRun.workspace_id == workspace_id)
        .group_by(EvaluationRun.prompt_id)
        .order_by(func.count(EvaluationRun.id).desc())
        .limit(10)
    ).all()
    trend_rows = session.exec(
        select(EvaluationRun)
        .where(EvaluationRun.workspace_id == workspace_id)
        .order_by(EvaluationRun.created_at.desc())
        .limit(50)
    ).all()

    return {
        "workspace_id": workspace_id,
        "total_prompts": total_prompts,
        "total_evaluations": total_evaluations,
        "total_ab_tests": total_ab_tests,
        "avg_score": round(float(avg_score), 2) if avg_score is not None else None,
        "avg_latency_ms": round(float(avg_latency), 1) if avg_latency is not None else None,
        "review_queue": review_queue,
        "production_prompts": production_prompts,
        "draft_prompts": draft_prompts,
        "approval_rate": round(production_prompts / total_prompts, 3) if total_prompts else 0,
        "recent_activity_count": recent_activity_count,
        "prompt_usage": [
            {
                "prompt_id": prompt_id,
                "evaluations": int(evaluations),
                "avg_score": round(float(avg), 2) if avg is not None else 0,
            }
            for prompt_id, evaluations, avg in usage_rows
        ],
        "trends": [
            {
                "created_at": row.created_at,
                "score": row.score,
                "latency_ms": row.latency_ms,
                "source": row.source,
                "prompt_id": row.prompt_id,
            }
            for row in reversed(trend_rows)
        ],
    }
