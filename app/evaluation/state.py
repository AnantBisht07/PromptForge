from typing import TypedDict


class EvalState(TypedDict):
    """
    The shape of data that flows through the evaluation graph.

    Each node in the graph receives this state and returns a partial
    update — LangGraph merges the updates automatically.

    Fields:
        prompt  – the original user prompt being evaluated
        output  – the LLM-generated response (filled by llm_node)
        score   – quality score between 1.0 and 10.0 (filled by scoring_node)
    """

    prompt: str
    output: str
    score: float
