from app.evaluation.state import EvalState
from app.services.llm_service import generate_output
from app.services.scoring_service import score_output


def llm_node(state: EvalState) -> dict:
    """
    Node 1 — LLM Generation

    Reads:  state["prompt"]
    Writes: state["output"]

    Calls the LLM service to generate a response for the prompt.
    LangGraph merges the returned dict back into the shared state so the
    next node can read state["output"] directly.
    """
    output = generate_output(state["prompt"])
    return {"output": output}


def scoring_node(state: EvalState) -> dict:
    """
    Node 2 — Output Scoring

    Reads:  state["prompt"], state["output"]
    Writes: state["score"]

    Evaluates how well the LLM output addresses the original prompt and
    returns a quality score in the 1.0–10.0 range.
    """
    score = score_output(state["prompt"], state["output"])
    return {"score": score}
