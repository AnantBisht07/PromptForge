import pandas as pd
import streamlit as st

from frontend.api.client import APIClient


def _decision_for(eval_id: str) -> dict:
    return st.session_state["feedback"].get(eval_id, {"decision": "pending", "comment": "", "reviewer": ""})


def _apply_decision(eval_id: str, decision: str, comment: str, reviewer: str):
    st.session_state["feedback"][eval_id] = {
        "decision": decision,
        "comment": comment,
        "reviewer": reviewer,
    }


def render(api: APIClient):
    user = st.session_state.get("user") or {}
    st.header("Reviewer queue")
    st.caption("Human-in-the-loop review of recent evaluations.")
    st.warning(
        "Comments are session-local. Persistence requires a `/feedback` endpoint and a `Feedback` table — neither exist in the backend yet.",
        icon="⚠️",
    )

    evaluations = st.session_state.get("evaluations", [])
    if not evaluations:
        st.info("No evaluations yet. Run an evaluation in the **Developer** or **A/B Testing** tab to populate this queue.")
        return

    threshold = st.slider("Show evaluations with score ≤", 1.0, 10.0, 5.0, 0.1)

    flagged = [e for e in evaluations if e["score"] <= threshold]

    counts_cols = st.columns(4)
    feedback = st.session_state.get("feedback", {})
    counts_cols[0].metric("Total evaluations", len(evaluations))
    counts_cols[1].metric("Flagged (≤ threshold)", len(flagged))
    counts_cols[2].metric("Approved", sum(1 for v in feedback.values() if v["decision"] == "approved"))
    counts_cols[3].metric("Rejected", sum(1 for v in feedback.values() if v["decision"] == "rejected"))

    if not flagged:
        st.success("Nothing flagged at this threshold. Lower it to triage more evaluations.")
        return

    st.subheader(f"{len(flagged)} evaluation(s) need review")
    for ev in flagged:
        decision = _decision_for(ev["id"])
        badge = {"approved": "✅ Approved", "rejected": "❌ Rejected", "pending": "⏳ Pending"}[decision["decision"]]
        with st.container(border=True):
            top = st.columns([3, 1, 1])
            top[0].markdown(f"**{ev['prompt_label']}** · v{ev['version_number']} · score **{ev['score']:.2f}** · {ev['latency_ms']:.0f} ms")
            top[1].markdown(badge)
            top[2].caption(ev["ts"])

            with st.expander("Prompt + LLM output"):
                st.markdown("**Prompt sent to /evaluate:**")
                st.code(ev["prompt"], language="markdown")
                st.markdown("**LLM output:**")
                st.write(ev["output"])

            comment = st.text_area(
                "Reviewer comment",
                value=decision["comment"],
                key=f"comment_{ev['id']}",
                height=80,
            )
            actions = st.columns(3)
            if actions[0].button("Approve", key=f"approve_{ev['id']}", use_container_width=True):
                _apply_decision(ev["id"], "approved", comment, user.get("user_id", ""))
                st.rerun()
            if actions[1].button("Reject", key=f"reject_{ev['id']}", use_container_width=True):
                _apply_decision(ev["id"], "rejected", comment, user.get("user_id", ""))
                st.rerun()
            if actions[2].button("Reset", key=f"reset_{ev['id']}", use_container_width=True):
                st.session_state["feedback"].pop(ev["id"], None)
                st.rerun()

    st.divider()
    if feedback:
        st.subheader("Decision log (this session)")
        rows = []
        for eval_id, fb in feedback.items():
            ev = next((e for e in evaluations if e["id"] == eval_id), None)
            rows.append({
                "eval_id": eval_id,
                "prompt": ev["prompt_label"] if ev else "—",
                "score": ev["score"] if ev else None,
                "decision": fb["decision"],
                "comment": fb["comment"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
