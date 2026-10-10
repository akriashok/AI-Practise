"""Supervisor/router: decides which specialist agent handles the question."""
from __future__ import annotations

import re
import time

from healthcare_agents.agents.common import history_text, llm_json, trace_step

AGENTS = {
    "data_explorer": "Ad-hoc questions about providers, members, plans, claims, encounters, labs, pharmacy, "
                     "prior auth or referrals answered by writing SQL (counts, lists, averages, top-N, lookups).",
    "reporting": "Summary, executive, KPI or impact reports for business review (claims, denials, provider network, "
                 "file operations).",
    "file_tracker": "Status/lifecycle of submitted files: where a file is in validation, approval or load stages, "
                    "failed/pending/rejected/stuck files, a specific file id like FS-20250012, files by a submitter.",
    "data_visualization": "Charts/graphs/visual analysis of submitted files per user: how many passed or failed "
                          "validation and how many reached the core layer, trends and funnels.",
}

_KEYWORDS = [
    ("data_visualization", r"\b(chart|plot|graph|visuali[sz]|dashboard|funnel|trend)\w*"),
    ("file_tracker", r"\bFS-\d+|\b(file|files|submission|submitted|validation|approval|load(ed|ing)?|core layer|staging|landing)\b"),
    ("reporting", r"\b(report|summary|summari[sz]e|executive|impact|kpi|business review|overview)\b"),
]


def keyword_route(question: str) -> str:
    for agent, pattern in _KEYWORDS:
        if re.search(pattern, question, re.I):
            return agent
    return "data_explorer"


def router_node(state: dict) -> dict:
    started = time.time()
    question = state["question"]
    options = "\n".join(f"- {k}: {v}" for k, v in AGENTS.items())
    fallback = keyword_route(question)
    result = llm_json(
        "You are the supervisor of a healthcare data multi-agent system. Pick the single best agent for the "
        f"user's request.\nAgents:\n{options}\n"
        'Return {"agent": "<agent name>", "reason": "<short reason>"}.',
        f"Conversation so far:\n{history_text(state.get('history'))}\n\nUser request: {question}",
        default={"agent": fallback, "reason": "keyword fallback"},
    )
    route = result.get("agent") if result.get("agent") in AGENTS else fallback
    reason = result.get("reason", "")
    return {
        "route": route,
        "route_reason": reason,
        "feedback": None,
        "reflection_count": 0,
        "approved": False,
        "sql": None,
        "table": [],
        "charts": [],
        "evidence": "",
        "error": None,
        "trace": [trace_step("router", started, decision=route, reason=reason)],
    }
