import time
from collections import Counter
from statistics import mean

import pandas as pd
import streamlit as st

from frontend.api.client import APIClient, APIError
from frontend.utils.charts import metric_grid, score_histogram


def _refresh_controls() -> tuple[bool, int]:
    left, right, spacer = st.columns([1, 1, 3])
    if left.button("Refresh", key="analytics_refresh", use_container_width=True):
        st.rerun()
    auto_refresh = right.checkbox("Auto refresh", key="analytics_auto")
    interval = 15
    if auto_refresh:
        interval = int(spacer.number_input(
            "Seconds",
            min_value=5,
            max_value=60,
            value=15,
            step=5,
            key="analytics_interval",
        ))
    return auto_refresh, interval


def render(api: APIClient):
    st.header("Analytics")
    auto_refresh, interval = _refresh_controls()

    try:
        analytics = api.analytics()
        prompts = api.workspace_prompts()
        members = api.workspace_members()
        activities = api.workspace_activity(limit=50)
    except APIError as e:
        st.error(f"Could not load analytics: {e.message}")
        return

    session_evaluations = st.session_state.get("evaluations", [])
    trends = analytics.get("trends", [])
    avg_score = analytics.get("avg_score")
    if avg_score is None and session_evaluations:
        avg_score = round(mean(e["score"] for e in session_evaluations), 2)
    avg_latency = analytics.get("avg_latency_ms")
    if avg_latency is None and session_evaluations:
        avg_latency = round(mean(e["latency_ms"] for e in session_evaluations), 1)

    metric_grid({
        "Members": len(members),
        "Prompts": analytics["total_prompts"],
        "Evaluations": analytics["total_evaluations"],
        "A/B tests": analytics["total_ab_tests"],
        "Review queue": analytics["review_queue"],
        "Production": analytics["production_prompts"],
        "Activity 24h": analytics["recent_activity_count"],
        "Approval rate": f"{round(analytics['approval_rate'] * 100)}%",
        "Avg eval score": avg_score if avg_score is not None else "-",
        "Avg latency": f"{avg_latency} ms" if avg_latency is not None else "-",
    })

    left, right = st.columns(2)
    with left:
        st.subheader("Prompt status")
        status_counts = Counter(prompt.get("status", "review") for prompt in prompts)
        status_df = pd.DataFrame(
            [{"status": key, "count": value} for key, value in sorted(status_counts.items())]
        )
        if status_df.empty:
            st.info("No prompt status data.")
        else:
            st.bar_chart(status_df.set_index("status"), height=260)
            st.dataframe(status_df, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Workspace roles")
        role_counts = Counter(member.get("role", "unknown") for member in members)
        role_df = pd.DataFrame(
            [{"role": key, "count": value} for key, value in sorted(role_counts.items())]
        )
        if role_df.empty:
            st.info("No member role data.")
        else:
            st.bar_chart(role_df.set_index("role"), height=260)
            st.dataframe(role_df, use_container_width=True, hide_index=True)

    st.subheader("Evaluation scores")
    if trends:
        score_histogram([item["score"] for item in trends])
        eval_df = pd.DataFrame([
            {
                "prompt_id": item.get("prompt_id"),
                "score": item["score"],
                "latency_ms": item["latency_ms"],
                "source": item["source"],
                "created_at": item["created_at"][:19],
            }
            for item in trends
        ])
        st.dataframe(eval_df, use_container_width=True, hide_index=True)
    elif session_evaluations:
        score_histogram([e["score"] for e in session_evaluations])
        eval_df = pd.DataFrame([
            {
                "id": e["id"],
                "prompt": e["prompt_label"],
                "version": e["version_number"],
                "score": e["score"],
                "latency_ms": e["latency_ms"],
                "source": e["source"],
                "ts": e["ts"],
            }
            for e in session_evaluations
        ])
        st.dataframe(eval_df, use_container_width=True, hide_index=True)
    else:
        st.info("No evaluations recorded yet.")

    st.subheader("Prompt usage")
    usage = analytics.get("prompt_usage", [])
    if usage:
        usage_df = pd.DataFrame(usage)
        st.bar_chart(usage_df.set_index("prompt_id")["evaluations"], height=240)
        st.dataframe(usage_df, use_container_width=True, hide_index=True)
    else:
        st.info("No prompt usage data yet.")

    st.subheader("Activity feed")
    if activities:
        activity_df = pd.DataFrame([
            {
                "event": item["event"],
                "user_id": item["user_id"],
                "created_at": item["created_at"][:19],
            }
            for item in activities
        ])
        st.dataframe(activity_df, use_container_width=True, hide_index=True)
    else:
        st.info("No activity recorded yet.")

    if auto_refresh:
        time.sleep(interval)
        st.rerun()
