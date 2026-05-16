from datetime import datetime

import pandas as pd
import streamlit as st

from frontend.api.client import APIClient, APIError
from frontend.utils.charts import score_trend


def _record_evaluation(prompt_id: int, version_number: int, prompt_label: str, result: dict):
    """Push an evaluation into session_state so Reviewer + Analyst tabs can see it."""
    evaluations = st.session_state.setdefault("evaluations", [])
    evaluations.append({
        "id": f"eval-{len(evaluations) + 1}",
        "prompt_id": prompt_id,
        "version_number": version_number,
        "prompt_label": prompt_label,
        "prompt": result["prompt"],
        "output": result["output"],
        "score": float(result["score"]),
        "latency_ms": float(result["latency_ms"]),
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "source": "developer",
    })


def _create_prompt_section(api: APIClient):
    with st.expander("➕ Create new prompt", expanded=False):
        with st.form("create_prompt"):
            content = st.text_area("Prompt content", height=120, placeholder="Explain transformer architecture to a 10 year old")
            submitted = st.form_submit_button("Create")
        if submitted:
            if not content.strip():
                st.warning("Prompt content cannot be empty.")
                return
            try:
                created = api.create_prompt(content.strip())
                st.success(f"Created prompt #{created['id']} (v1).")
                st.rerun()
            except APIError as e:
                st.error(f"Failed: {e.message}")


def _semantic_search_section(api: APIClient):
    st.subheader("🔍 Semantic search")
    st.caption("Mock embeddings — results are deterministic but not semantically meaningful (see vector_service.py).")
    query = st.text_input("Search query", key="dev_search_query", placeholder="explain AI concepts simply")
    if st.button("Search", key="dev_search_btn") and query.strip():
        try:
            results = api.search(query.strip())
        except APIError as e:
            st.error(f"Search failed: {e.message}")
            return
        if not results:
            st.info("No matches.")
            return
        df = pd.DataFrame([
            {"prompt_id": r["prompt_id"], "score": round(r["score"], 4), "content": (r.get("content") or "")[:160]}
            for r in results
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


def render(api: APIClient):
    st.header("Developer workspace")
    st.caption("Iterate on prompts: create, version, evaluate, and search.")

    _create_prompt_section(api)

    try:
        prompts = api.list_prompts()
    except APIError as e:
        st.error(f"Could not load prompts: {e.message}")
        return

    if not prompts:
        st.info("No prompts yet. Use **Create new prompt** above to get started.")
        return

    label_for = lambda p: f"#{p['id']} — {p['content'][:60]}{'…' if len(p['content']) > 60 else ''}"
    chosen_idx = st.selectbox(
        "Select a prompt",
        options=range(len(prompts)),
        format_func=lambda i: label_for(prompts[i]),
        key="dev_prompt_idx",
    )
    prompt = prompts[chosen_idx]
    versions = sorted(prompt.get("versions", []), key=lambda v: v["version_number"])

    meta_cols = st.columns(4)
    meta_cols[0].metric("Prompt ID", prompt["id"])
    meta_cols[1].metric("Versions", len(versions))
    meta_cols[2].metric("Status", prompt.get("status", "review"))
    meta_cols[3].metric("Created", prompt["created_at"][:10])

    with st.container(border=True):
        st.markdown("**Latest content**")
        st.code(prompt["content"], language="markdown")

    with st.expander("Edit prompt", expanded=False):
        with st.form(f"edit_prompt_{prompt['id']}"):
            edited = st.text_area("Prompt content", value=prompt["content"], height=120)
            status = st.selectbox(
                "Status",
                options=["review", "draft"],
                index=0 if prompt.get("status") != "draft" else 1,
                key=f"edit_status_{prompt['id']}",
            )
            submitted = st.form_submit_button("Save new version", use_container_width=True)
        if submitted:
            if not edited.strip():
                st.warning("Prompt content cannot be empty.")
            else:
                try:
                    updated = api.update_prompt(prompt["id"], edited.strip(), status=status)
                    st.success(f"Saved prompt #{updated['id']} as a new version.")
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed: {e.message}")

    st.subheader("Version history")
    if versions:
        df = pd.DataFrame([
            {"version": v["version_number"], "created_at": v["created_at"][:19], "content": v["content"][:120]}
            for v in versions
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No versions registered (unexpected — every prompt should have v1).")

    action_cols = st.columns(2)

    with action_cols[0]:
        if st.button("⚡ Evaluate latest version", key="dev_eval_latest", use_container_width=True):
            latest = versions[-1] if versions else {"version_number": 1, "content": prompt["content"]}
            try:
                result = api.evaluate(latest["content"], prompt_id=prompt["id"])
                _record_evaluation(prompt["id"], latest["version_number"], label_for(prompt), result)
                st.success(f"Score: {result['score']:.2f}  ·  Latency: {result['latency_ms']:.0f} ms")
                with st.expander("LLM output", expanded=True):
                    st.write(result["output"])
            except APIError as e:
                st.error(f"Evaluation failed: {e.message}")

    with action_cols[1]:
        if st.button("📈 Score trend across versions", key="dev_eval_trend", use_container_width=True):
            if not versions:
                st.warning("No versions to chart.")
            else:
                with st.spinner("Evaluating each version…"):
                    nums, scores = [], []
                    for v in versions:
                        try:
                            r = api.evaluate(v["content"], prompt_id=prompt["id"])
                            _record_evaluation(prompt["id"], v["version_number"], label_for(prompt), r)
                            nums.append(v["version_number"])
                            scores.append(r["score"])
                        except APIError as e:
                            st.error(f"v{v['version_number']} failed: {e.message}")
                if scores:
                    st.info("Computed live this session — historical trend data requires backend persistence.")
                    score_trend(nums, scores)

    st.divider()
    _semantic_search_section(api)
