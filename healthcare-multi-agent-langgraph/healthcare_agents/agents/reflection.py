"""Reflection Agent: reviews specialist outputs and triggers corrections before they reach the user."""
from __future__ import annotations

import json
import time

from healthcare_agents.agents.common import llm_json, trace_step
from healthcare_agents.config import MAX_REFLECTIONS

REVIEW_SYSTEM = """You are a strict QA reviewer in a healthcare data multi-agent system.
Check the specialist agent's output against the user's question and the supporting data:
1. Does it directly answer the question asked (right metric, filters, grouping, time period)?
2. Are all numbers, ids, names and dates consistent with the supporting data (no hallucinated figures)?
   Derived values (sums, percentages, differences) of supporting numbers are fine. General domain explanations
   (e.g. what a pipeline stage or denial category means) and recommendations are allowed and are NOT hallucinations.
3. For SQL: does the query logic match the question (joins, filters, aggregation)?
4. Is it clear, complete and free of PHI over-exposure (no more personal detail than asked)?
5. If the SQL returned 0 rows, check whether literal filter values (names, codes, statuses) match the sample values
   in the data; if a mismatch is likely, reject and say which value to fix.
Charts, generated SQL and data tables are displayed to the user by the UI next to the text, so the text does not
need to contain them. Approve when the answer is correct and useful even if it could be phrased better.
Return {"approved": true|false, "score": 1-10, "issues": "<short list or empty>", "feedback": "<specific fix instructions or empty>"}"""


def reflection_node(state: dict) -> dict:
    started = time.time()
    count = state.get("reflection_count", 0) + 1
    if state.get("error"):
        verdict = {"approved": False, "score": 1, "issues": state["error"],
                   "feedback": f"The agent failed with error: {state['error']}. Fix the query/approach."}
    elif not (state.get("answer") or "").strip():
        verdict = {"approved": False, "score": 1, "issues": "empty answer", "feedback": "Produce a complete answer."}
    else:
        evidence = state.get("evidence") or json.dumps(state.get("table", [])[:25], default=str)
        verdict = llm_json(
            REVIEW_SYSTEM,
            f"Agent: {state.get('route')}\nUser question: {state['question']}\n\n"
            f"SQL used: {state.get('sql') or '(curated queries)'}\n\n"
            f"Supporting data the agent was given (the ONLY source of truth):\n{evidence[:12000]}\n\n"
            f"Agent answer:\n{state.get('answer', '')[:5000]}",
            default={"approved": True, "score": 7, "issues": "reviewer response unparseable", "feedback": ""},
        )
    approved = bool(verdict.get("approved"))
    retry = not approved and count <= MAX_REFLECTIONS
    return {
        "approved": approved,
        "reflection_count": count,
        "feedback": verdict.get("feedback") if retry else None,
        "trace": [trace_step("reflection", started, review_round=count, approved=approved, score=verdict.get("score"),
                             issues=verdict.get("issues"), action="send back for correction" if retry else "release to user")],
    }


def after_reflection(state: dict) -> str:
    return state["route"] if state.get("feedback") else "end"
