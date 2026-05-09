from collections import defaultdict
from statistics import mean

import pandas as pd
import streamlit as st

from frontend.api.client import APIClient, APIError
from frontend.utils.charts import metric_grid, score_histogram


def render(api: APIClient):
    st.header("Analyst dashboard")
    st.caption("Operational visibility into the AI platform.")
    st.info(
        "Metrics aggregate evaluations performed in **this session**. "
        "Cross-session analytics require persisting eval runs (no `EvaluationRun` table exists yet).",
        icon="ℹ️",
    )

    if st.button("🔄 Refresh prompt list", key="analyst_refresh"):
        st.rerun()

    try:
        prompts = api.list_prompts()
    except APIError as e:
        st.error(f"Could not load prompts: {e.message}")
        prompts = []

    evaluations = st.session_state.get("evaluations", [])
    feedback = st.session_state.get("feedback", {})

    total_prompts = len(prompts)
    total_evals = len(evaluations)
    avg_score = round(mean(e["score"] for e in evaluations), 2) if evaluations else "—"
    avg_latency = f"{round(mean(e['latency_ms'] for e in evaluations))} ms" if evaluations else "—"

    metric_grid({
        "Total prompts": total_prompts,
        "Evaluations (session)": total_evals,
        "Avg score": avg_score,
        "Avg latency": avg_latency,
    })

    decision_cols = st.columns(3)
    decision_cols[0].metric("Approved", sum(1 for v in feedback.values() if v["decision"] == "approved"))
    decision_cols[1].metric("Rejected", sum(1 for v in feedback.values() if v["decision"] == "rejected"))
    decision_cols[2].metric("Pending", max(0, total_evals - len(feedback)))

    if not evaluations:
        st.warning("Run evaluations in the Developer or A/B Testing tabs to populate the charts below.")
        return

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Top prompts by avg score")
        grouped: dict[str, list[float]] = defaultdict(list)
        for e in evaluations:
            grouped[e["prompt_label"]].append(e["score"])
        if grouped:
            rows = sorted(
                ({"prompt": k, "avg_score": round(mean(v), 2), "evals": len(v)} for k, v in grouped.items()),
                key=lambda r: r["avg_score"], reverse=True,
            )[:5]
            df = pd.DataFrame(rows).set_index("prompt")
            st.bar_chart(df["avg_score"], height=280)
            st.dataframe(df, use_container_width=True)

    with right:
        st.subheader("Score distribution")
        score_histogram([e["score"] for e in evaluations])

    st.subheader("Latency over evaluations")
    latency_df = pd.DataFrame({
        "eval #": list(range(1, len(evaluations) + 1)),
        "latency_ms": [e["latency_ms"] for e in evaluations],
    }).set_index("eval #")
    st.line_chart(latency_df, height=240)

    with st.expander("Raw evaluation log"):
        st.dataframe(
            pd.DataFrame([
                {
                    "id": e["id"],
                    "prompt": e["prompt_label"],
                    "version": e["version_number"],
                    "score": e["score"],
                    "latency_ms": e["latency_ms"],
                    "source": e["source"],
                    "ts": e["ts"],
                }
                for e in evaluations
            ]),
            use_container_width=True,
            hide_index=True,
        )
