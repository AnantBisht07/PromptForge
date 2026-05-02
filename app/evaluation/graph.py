"""
Evaluation pipeline built with LangGraph.

Graph topology:

    [START] → llm_node → scoring_node → [END]

LangSmith tracing:
    When LANGCHAIN_API_KEY is set in your .env, every graph.invoke() call
    is automatically recorded in LangSmith.  You can see:
      • the full input/output at each node
      • timing and token usage (when using a real LLM)
      • the complete execution trace linked to your project

    Nothing extra is required in the code — LangGraph reads the
    LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY environment variables
    at import time and enables tracing automatically.
"""

import os
from langgraph.graph import StateGraph

from app.evaluation.state import EvalState
from app.evaluation.nodes import llm_node, scoring_node
from app.core.config import settings

# ── LangSmith setup ──────────────────────────────────────────────────────────
# Setting these env vars is all that's needed — LangGraph picks them up
# automatically.  If LANGCHAIN_API_KEY is empty we skip tracing so the app
# works without a LangSmith account.
if settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

# ── Graph definition ─────────────────────────────────────────────────────────
builder = StateGraph(EvalState)

# Register nodes — each is a plain Python function
builder.add_node("llm", llm_node)
builder.add_node("scorer", scoring_node)

# Wire up the execution order
builder.set_entry_point("llm")       # graph starts here
builder.add_edge("llm", "scorer")    # llm output feeds into scorer
builder.set_finish_point("scorer")   # graph ends here

# Compile into a runnable — call graph.invoke({"prompt": "..."}) to run it
graph = builder.compile()
