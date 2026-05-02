# PromptForge — Week 26: Evaluation Engine

> **Program:** AI & Full Stack Engineering  
> **Week:** 26  
> **Date:** 2 May 2026  
> **Built on top of:** Week 25 — Multi-Tenant Prompt Management API

---

## What We Are Building This Week

In Week 25 we built the backbone of PromptForge — users, prompts, versioning, and semantic search.

**This week we answer the next natural question: how do you know if a prompt is any good?**

We are building an **Evaluation Engine** — a pipeline that takes any prompt, runs it through an LLM, scores the quality of the output, and logs the entire process for observability. This is the kind of system that teams at AI companies use to test prompts before shipping them to users.

---

## The Core Idea

```
User submits a prompt
        │
        ▼
  ┌─────────────┐
  │  LLM Node   │  ← sends the prompt to an LLM, gets back a response
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Scorer Node │  ← measures how relevant the response is to the prompt
  └──────┬──────┘
         │
         ▼
  Return { prompt, output, score }   +   full trace logged to LangSmith
```

This pipeline is built using **LangGraph** — a framework for defining AI workflows as graphs of nodes and edges. Think of it as a flowchart where each box is a Python function.

---

## What You Will Learn

| Concept | What You Will Build |
|---|---|
| **LangGraph** | Define an evaluation workflow as a directed graph |
| **Graph State** | Pass data between nodes using a typed state object |
| **LLM as a Service** | Call OpenAI (or use a mock) inside a graph node |
| **Scoring Logic** | Programmatically measure prompt-output relevance |
| **LangSmith Tracing** | Log every step of an AI pipeline for observability |
| **Modular Node Design** | Write nodes as pure functions that are easy to test and swap |

---

## New Files Created

### `app/evaluation/` — the evaluation pipeline module

| File | What It Does |
|---|---|
| [app/evaluation/\_\_init\_\_.py](app/evaluation/__init__.py) | Makes `evaluation` a Python package |
| [app/evaluation/state.py](app/evaluation/state.py) | Defines `EvalState` — the data shape that flows through the graph |
| [app/evaluation/nodes.py](app/evaluation/nodes.py) | Two graph nodes: `llm_node` (generate) and `scoring_node` (score) |
| [app/evaluation/graph.py](app/evaluation/graph.py) | Assembles the LangGraph pipeline and wires up LangSmith tracing |

### `app/services/` — new services added

| File | What It Does |
|---|---|
| [app/services/llm_service.py](app/services/llm_service.py) | `generate_output(prompt)` — calls OpenAI or returns a mock response |
| [app/services/scoring_service.py](app/services/scoring_service.py) | `score_output(prompt, output)` — returns a quality score from 1.0 to 10.0 |

### `app/routers/` — new route added

| File | What It Does |
|---|---|
| [app/routers/eval_router.py](app/routers/eval_router.py) | `POST /evaluate` — accepts a prompt, runs the graph, returns the result |

---

## Files Updated

| File | What Changed |
|---|---|
| [app/core/config.py](app/core/config.py) | Added `OPENAI_API_KEY`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` settings |
| [app/main.py](app/main.py) | Imported and registered `eval_router` |
| [requirements.txt](requirements.txt) | Added `langgraph`, `langchain`, `langsmith`, `openai` |
| [.env.example](.env.example) | Documented the two new optional environment variables |

---

## Architecture Deep Dive

### 1. State — the data contract of the graph

```python
# app/evaluation/state.py
class EvalState(TypedDict):
    prompt: str   # set by the caller
    output: str   # filled in by llm_node
    score: float  # filled in by scoring_node
```

Every node receives the current state and returns a **partial update**. LangGraph merges it automatically. This is how data flows from node to node without you passing arguments manually.

---

### 2. Nodes — pure Python functions

```python
# app/evaluation/nodes.py

def llm_node(state: EvalState) -> dict:
    output = generate_output(state["prompt"])
    return {"output": output}          # partial update

def scoring_node(state: EvalState) -> dict:
    score = score_output(state["prompt"], state["output"])
    return {"score": score}            # partial update
```

Each node does exactly one thing. This makes them easy to:
- Test independently
- Swap out (e.g. replace the mock LLM with GPT-4 in one line)
- Reorder in the graph

---

### 3. Graph — the pipeline definition

```python
# app/evaluation/graph.py
builder = StateGraph(EvalState)

builder.add_node("llm", llm_node)
builder.add_node("scorer", scoring_node)

builder.set_entry_point("llm")       # starts here
builder.add_edge("llm", "scorer")    # then goes here
builder.set_finish_point("scorer")   # ends here

graph = builder.compile()
```

The graph is compiled once when the module is imported and reused across all requests — the same compiled object handles every `/evaluate` call.

---

### 4. Scoring — how the number is calculated

```
score = (keyword_coverage × 0.7) + (length_bonus × 0.3)
      → mapped to the range [1.0, 10.0]
```

**Keyword coverage:** what fraction of meaningful words from the prompt also appear in the output? If the prompt says "Explain neural networks" and the output never mentions "neural" or "networks", that's a low score.

**Length bonus:** very short outputs are penalised. The bonus caps at 50 words so the scorer can't be gamed by just generating a wall of text.

This is an intentionally simple heuristic — it's transparent, debuggable, and good enough for learning. In production, you would replace this with an LLM-as-judge call.

---

### 5. LangSmith tracing — observability for free

When `LANGCHAIN_API_KEY` is set in `.env`, these two environment variables are set at startup:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your key>
```

LangGraph reads these automatically. Every `graph.invoke()` call sends a trace to LangSmith containing:
- The initial input
- What each node received and returned
- Timing for each step
- The final output

No extra code is needed. This is a good example of **instrumentation through configuration** — the business logic stays clean.

---

## New API Endpoint

### `POST /evaluate`

**Requires:** Bearer token (JWT from `/auth/login`)

**Request:**
```json
{
  "prompt": "Explain neural networks to a beginner"
}
```

**Response:**
```json
{
  "prompt": "Explain neural networks to a beginner",
  "output": "AI response to: Explain neural networks to a beginner",
  "score": 6.43
}
```

---

## How to Run

### Step 1 — Install new dependencies
```bash
pip install langgraph langchain langsmith openai
```

### Step 2 — Start the server
```bash
uvicorn app.main:app --reload
```

### Step 3 — Log in and get a token
```bash
POST /auth/login
{ "username": "alice", "password": "pass123" }
```

### Step 4 — Run an evaluation
```bash
POST /evaluate
Authorization: Bearer <your_token>
{ "prompt": "Explain AI simply" }
```

### Step 5 — (Optional) Enable LangSmith tracing

Add to `.env`:
```
LANGCHAIN_API_KEY=lsv2_your_key_here
LANGCHAIN_PROJECT=promptforge-eval
```

Then open [https://smith.langchain.com](https://smith.langchain.com), go to your project, and watch traces appear in real time as you call `/evaluate`.

---

## Optional: Use a Real LLM

By default the evaluation engine returns a mock response. To use OpenAI:

1. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
2. Restart the server.

The `llm_service.py` checks for the key at runtime — no code changes needed.

---

## Dependency Map (Week 26 only)

```
POST /evaluate
    └── eval_router.py
            └── graph.py  (LangGraph pipeline)
                    ├── llm_node  ──── llm_service.py  ──── OpenAI / mock
                    └── scoring_node ── scoring_service.py
```

Everything new sits inside `app/evaluation/` and `app/services/`. The existing Week 25 code (`auth`, `prompts`, `users`) is completely untouched.

---

## What's Next

- [ ] Add more scoring signals (coherence, grammar, length penalty)
- [ ] Store evaluation results in the database and link them to prompts
- [ ] Add a `GET /evaluate/history` to review past evaluation runs
- [ ] Replace the keyword scorer with an LLM-as-judge (GPT-4 scores GPT-3.5's output)
- [ ] Add a batch evaluation endpoint to score multiple prompts at once
