from datetime import datetime
from statistics import mean

import pandas as pd
import streamlit as st

from frontend.api.client import APIClient, APIError
from frontend.utils.charts import ab_bar


def _record_eval(prompt_id: int, version_number: int, prompt_label: str, result: dict, source: str):
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
        "source": source,
    })


def render(api: APIClient):
    st.header("A/B Testing")
    st.caption("Compare two versions of the same prompt with a shared test input.")
    st.info(
        "A/B testing is orchestrated client-side: each round calls `/evaluate` once per version. "
        "The backend's existing LangGraph pipeline (and LangSmith tracing if configured) handles every run.",
        icon="🧪",
    )

    try:
        prompts = api.list_prompts()
    except APIError as e:
        st.error(f"Could not load prompts: {e.message}")
        return

    if not prompts:
        st.info("No prompts available. Create one in the **Developer** tab first.")
        return

    label_for = lambda p: f"#{p['id']} — {p['content'][:60]}{'…' if len(p['content']) > 60 else ''}"

    chosen_idx = st.selectbox(
        "Prompt",
        options=range(len(prompts)),
        format_func=lambda i: label_for(prompts[i]),
        key="ab_prompt_idx",
    )
    prompt = prompts[chosen_idx]
    versions = sorted(prompt.get("versions", []), key=lambda v: v["version_number"])

    if len(versions) < 2:
        st.warning(
            f"This prompt has only {len(versions)} version. A/B testing needs at least 2. "
            "Add another version (extend the backend with PUT /prompts/{id}, or recreate the prompt) and come back.",
            icon="⚠️",
        )
        with st.expander("Why?"):
            st.write(
                "The current backend doesn't expose a prompt-update route, so versioning happens only on `POST /prompts/create`. "
                "Each `create` call produces a brand-new prompt at v1 — versions live under one prompt id. "
                "The next iteration of the platform should add `PUT /prompts/{id}` to bump version_number on edits."
            )
        return

    col_a, col_b = st.columns(2)
    with col_a:
        version_a_idx = st.selectbox(
            "Version A",
            options=range(len(versions)),
            format_func=lambda i: f"v{versions[i]['version_number']}",
            key="ab_version_a",
        )
    with col_b:
        default_b = 1 if len(versions) > 1 else 0
        version_b_idx = st.selectbox(
            "Version B",
            options=range(len(versions)),
            format_func=lambda i: f"v{versions[i]['version_number']}",
            index=default_b,
            key="ab_version_b",
        )

    if version_a_idx == version_b_idx:
        st.warning("Pick two different versions.")
        return

    version_a = versions[version_a_idx]
    version_b = versions[version_b_idx]

    test_input = st.text_area(
        "Shared test input",
        placeholder="Explain AI to beginners",
        height=100,
        key="ab_test_input",
    )
    rounds = int(st.number_input("Rounds", min_value=1, max_value=20, value=5, step=1, key="ab_rounds"))

    if not st.button("▶️ Run A/B Test", key="ab_run", use_container_width=True):
        return

    if not test_input.strip():
        st.warning("Test input cannot be empty.")
        return

    label = label_for(prompt)
    a_results, b_results = [], []
    progress = st.progress(0.0, text="Running…")
    for i in range(rounds):
        prompt_a = f"{version_a['content']}\n\n{test_input.strip()}"
        prompt_b = f"{version_b['content']}\n\n{test_input.strip()}"
        try:
            r_a = api.evaluate(prompt_a)
            _record_eval(prompt["id"], version_a["version_number"], label, r_a, "ab_test_A")
            a_results.append(r_a)
        except APIError as e:
            st.error(f"Round {i+1} A failed: {e.message}")
            return
        try:
            r_b = api.evaluate(prompt_b)
            _record_eval(prompt["id"], version_b["version_number"], label, r_b, "ab_test_B")
            b_results.append(r_b)
        except APIError as e:
            st.error(f"Round {i+1} B failed: {e.message}")
            return
        progress.progress((i + 1) / rounds, text=f"Round {i + 1}/{rounds}")

    progress.empty()

    a_scores = [r["score"] for r in a_results]
    b_scores = [r["score"] for r in b_results]
    a_lat = [r["latency_ms"] for r in a_results]
    b_lat = [r["latency_ms"] for r in b_results]
    a_wins = sum(1 for s_a, s_b in zip(a_scores, b_scores) if s_a > s_b)
    b_wins = sum(1 for s_a, s_b in zip(a_scores, b_scores) if s_b > s_a)
    ties = rounds - a_wins - b_wins
    total = max(1, a_wins + b_wins)

    a_avg = round(mean(a_scores), 2)
    b_avg = round(mean(b_scores), 2)
    winner = "A" if a_avg > b_avg else "B" if b_avg > a_avg else "Tie"

    st.divider()
    st.subheader("Results")

    if winner == "Tie":
        st.success("🟰 It's a tie — no version dominates on average score.")
    else:
        won_label = f"v{version_a['version_number']}" if winner == "A" else f"v{version_b['version_number']}"
        st.success(f"🏆 Winner: **Version {winner} ({won_label})** — avg score {max(a_avg, b_avg):.2f}")

    cards = st.columns(3)
    cards[0].metric(
        f"Avg score  ·  A vs B",
        f"{a_avg:.2f}  vs  {b_avg:.2f}",
        delta=f"{(a_avg - b_avg):+.2f} (A − B)",
    )
    cards[1].metric(
        f"Avg latency",
        f"{round(mean(a_lat))} vs {round(mean(b_lat))} ms",
    )
    cards[2].metric(
        "Win rate (A / B / Ties)",
        f"{a_wins}/{b_wins}/{ties}",
        delta=f"{round(100 * a_wins / total)}% vs {round(100 * b_wins / total)}%",
    )

    st.subheader("Per-round scores")
    ab_bar(a_scores, b_scores)

    with st.expander("Raw outputs per round"):
        rows = []
        for i, (ra, rb) in enumerate(zip(a_results, b_results), 1):
            rows.append({"round": i, "side": "A", "score": ra["score"], "latency_ms": ra["latency_ms"], "output": ra["output"][:200]})
            rows.append({"round": i, "side": "B", "score": rb["score"], "latency_ms": rb["latency_ms"], "output": rb["output"][:200]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
