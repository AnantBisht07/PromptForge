from typing import Sequence

import pandas as pd
import streamlit as st


def score_trend(version_numbers: Sequence[int], scores: Sequence[float]):
    """Line chart of evaluation score across prompt versions."""
    if not version_numbers:
        st.info("No versions to chart yet.")
        return
    df = pd.DataFrame({"version": version_numbers, "score": scores}).set_index("version")
    st.line_chart(df, height=260)


def ab_bar(rounds_a: Sequence[float], rounds_b: Sequence[float]):
    """Grouped bar chart: per-round scores for Version A vs B."""
    rounds = list(range(1, max(len(rounds_a), len(rounds_b)) + 1))
    df = pd.DataFrame({"round": rounds, "Version A": rounds_a, "Version B": rounds_b}).set_index("round")
    st.bar_chart(df, height=300)


def metric_grid(metrics: dict[str, str | float | int]):
    """Render a row of st.metric tiles."""
    if not metrics:
        return
    items = list(metrics.items())
    for start in range(0, len(items), 4):
        cols = st.columns(min(4, len(items) - start))
        for col, (label, value) in zip(cols, items[start:start + 4]):
            col.metric(label, value)


def score_histogram(scores: Sequence[float], bins: int = 10):
    """Distribution of evaluation scores."""
    if not scores:
        st.info("No evaluations yet.")
        return
    series = pd.Series(scores)
    binned = pd.cut(series, bins=bins).value_counts().sort_index()
    df = pd.DataFrame({"count": binned.values}, index=[str(i) for i in binned.index])
    st.bar_chart(df, height=240)
