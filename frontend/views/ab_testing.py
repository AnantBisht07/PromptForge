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
        "A/B tests now run through the backend `/ab-test` API. The backend calls the "
        "existing LangGraph evaluation pipeline, records runs for analytics, and logs "
        "LangSmith traces when configured.",
    )

    try:
        prompts = api.list_prompts()
    except APIError as e:
        st.error(f"Could not load prompts: {e.message}")
        return

    if not prompts:
        st.info("No prompts available. Create one in the Developer tab first.")
        return

    label_for = lambda p: f"#{p['id']} - {p['content'][:60]}{'...' if len(p['content']) > 60 else ''}"

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
            "Add another version from the Developer tab and come back.",
        )
        with st.expander("Why?"):
            st.write(
                "A/B testing compares two versions under the same prompt id. "
                "Use Edit prompt in the Developer tab to create v2 or later."
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
        version_b_idx = st.selectbox(
            "Version B",
            options=range(len(versions)),
            format_func=lambda i: f"v{versions[i]['version_number']}",
            index=1,
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

    if not st.button("Run A/B Test", key="ab_run", use_container_width=True):
        return

    if not test_input.strip():
        st.warning("Test input cannot be empty.")
        return

    try:
        with st.spinner("Running backend A/B test..."):
            result = api.run_ab_test(
                prompt_id=prompt["id"],
                version_a=version_a["version_number"],
                version_b=version_b["version_number"],
                test_input=test_input.strip(),
                rounds=rounds,
            )
    except APIError as e:
        st.error(f"A/B test failed: {e.message}")
        return

    label = label_for(prompt)
    for item in result["evaluations"]:
        version_number = version_a["version_number"] if item["side"] == "A" else version_b["version_number"]
        _record_eval(prompt["id"], version_number, label, item, f"ab_test_{item['side']}")

    a_rows = [item for item in result["evaluations"] if item["side"] == "A"]
    b_rows = [item for item in result["evaluations"] if item["side"] == "B"]
    a_scores = [float(item["score"]) for item in a_rows]
    b_scores = [float(item["score"]) for item in b_rows]
    a_lat = [float(item["latency_ms"]) for item in a_rows]
    b_lat = [float(item["latency_ms"]) for item in b_rows]
    a_wins = sum(1 for s_a, s_b in zip(a_scores, b_scores) if s_a > s_b)
    b_wins = sum(1 for s_a, s_b in zip(a_scores, b_scores) if s_b > s_a)
    ties = rounds - a_wins - b_wins
    total = max(1, a_wins + b_wins)

    st.divider()
    st.subheader("Results")

    if result["winner"] == "Tie":
        st.success("Tie: no version dominates on average score.")
    else:
        won_label = f"v{version_a['version_number']}" if result["winner"] == "A" else f"v{version_b['version_number']}"
        st.success(
            f"Winner: Version {result['winner']} ({won_label}) "
            f"with avg score {max(result['avg_score_a'], result['avg_score_b']):.2f}"
        )

    cards = st.columns(3)
    cards[0].metric(
        "Avg score A vs B",
        f"{result['avg_score_a']:.2f} vs {result['avg_score_b']:.2f}",
        delta=f"{(result['avg_score_a'] - result['avg_score_b']):+.2f} A-B",
    )
    cards[1].metric(
        "Avg latency",
        f"{round(mean(a_lat))} vs {round(mean(b_lat))} ms",
    )
    cards[2].metric(
        "Win rate A/B/Ties",
        f"{a_wins}/{b_wins}/{ties}",
        delta=f"{round(100 * a_wins / total)}% vs {round(100 * b_wins / total)}%",
    )

    st.subheader("Per-round scores")
    ab_bar(a_scores, b_scores)

    with st.expander("Raw outputs per round"):
        rows = [
            {
                "round": item["round"],
                "side": item["side"],
                "score": item["score"],
                "latency_ms": item["latency_ms"],
                "output": item["output"][:200],
            }
            for item in result["evaluations"]
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
