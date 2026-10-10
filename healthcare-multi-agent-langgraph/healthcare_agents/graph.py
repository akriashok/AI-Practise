"""LangGraph wiring: router -> specialist agent -> reflection -> (retry agent | END)."""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from healthcare_agents.agents import (after_reflection, data_explorer_node, file_tracker_node, reflection_node,
                                      reporting_node, router_node, visualization_node)
from healthcare_agents.db import ensure_db
from healthcare_agents.state import AgentState

SPECIALISTS = {
    "data_explorer": data_explorer_node,
    "reporting": reporting_node,
    "file_tracker": file_tracker_node,
    "data_visualization": visualization_node,
}


@lru_cache(maxsize=1)
def build_graph():
    ensure_db()
    g = StateGraph(AgentState)
    g.add_node("router", router_node)
    for name, fn in SPECIALISTS.items():
        g.add_node(name, fn)
        g.add_edge(name, "reflection")
    g.add_node("reflection", reflection_node)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", lambda s: s["route"], {k: k for k in SPECIALISTS})
    g.add_conditional_edges("reflection", after_reflection, {**{k: k for k in SPECIALISTS}, "end": END})
    return g.compile()


def ask(question: str, history: list[dict[str, str]] | None = None) -> dict:
    return build_graph().invoke({"question": question, "history": history or [], "trace": []})


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    q = " ".join(sys.argv[1:]) or "How many active providers are there by specialty?"
    out = ask(q)
    for step in out["trace"]:
        print(step)
    print("\nSQL:", out.get("sql"))
    print("\n" + out["answer"])
