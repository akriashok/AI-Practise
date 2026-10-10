"""Streamlit UI for the Healthcare Multi-Agent System (LangGraph)."""
from __future__ import annotations

import pandas as pd
import plotly.io as pio
import streamlit as st

from healthcare_agents.db import ensure_db, table_counts
from healthcare_agents.graph import ask, build_graph

st.set_page_config(page_title="Healthcare Multi-Agent System", page_icon="🩺", layout="wide")
ensure_db()

AGENT_LABELS = {
    "router": "Supervisor / Router",
    "data_explorer": "Data Explorer Agent (NL2SQL)",
    "reporting": "Reporting Agent",
    "file_tracker": "File Tracker Agent",
    "data_visualization": "Data Visualization Agent",
    "reflection": "Reflection Agent",
}
EXAMPLES = {
    "Data Explorer": ["How many active providers are there in each specialty?",
                      "Top 10 members by total paid claims in 2026 with their plan name",
                      "Which providers have credentials expiring in the next 90 days?",
                      "Average length of stay for inpatient encounters by facility type"],
    "Reporting": ["Create an impact report on claim denials for the business review",
                  "Give me an executive summary of the provider network",
                  "Summary report of the file ingestion pipeline"],
    "File Tracker": ["Where is file FS-20250007 in the pipeline?",
                     "Which files submitted by pkumar failed validation and why?",
                     "Show files pending approval"],
    "Data Visualization": ["Chart how many files each user passed or failed validation and reached core",
                           "Visualize file outcomes for CLAIMS_837 files",
                           "Plot validation results for asmith and jchen"],
}


@st.cache_resource
def _graph():
    return build_graph()


def render_result(res: dict, key: str) -> None:
    st.markdown(res["answer"])
    for i, chart in enumerate(res.get("charts") or []):
        st.plotly_chart(pio.from_json(chart), width="stretch", key=f"{key}-chart-{i}")
    if res.get("sql"):
        with st.expander("Generated SQL"):
            st.code(res["sql"], language="sql")
    if res.get("table"):
        with st.expander(f"Data ({len(res['table'])} rows)"):
            st.dataframe(pd.DataFrame(res["table"]), width="stretch", hide_index=True)
    with st.expander("Agent trace"):
        for step in res.get("trace", []):
            label = AGENT_LABELS.get(step["agent"], step["agent"])
            details = {k: v for k, v in step.items() if k not in ("agent",)}
            st.markdown(f"**{label}**")
            st.json(details, expanded=False)
    badge = "✅ Approved by Reflection Agent" if res.get("approved") else "⚠️ Released after max review rounds"
    st.caption(f"{AGENT_LABELS.get(res.get('route'), res.get('route'))} · {badge} · review rounds: {res.get('reflection_count', 0)}")


with st.sidebar:
    st.title("🩺 Healthcare Multi-Agent")
    st.caption("LangGraph · LangChain · SQLite · OpenRouter LLM")
    st.markdown("**Agents**\n"
                "- Data Explorer (NL2SQL)\n- Reporting\n- File Tracker\n- Data Visualization\n- Reflection (QA)")
    st.divider()
    st.subheader("Try an example")
    for group, qs in EXAMPLES.items():
        with st.expander(group):
            for q in qs:
                if st.button(q, key=f"ex-{q}", width="stretch"):
                    st.session_state.pending = q
    st.divider()
    with st.expander("Database: 40 healthcare tables"):
        st.dataframe(table_counts(), hide_index=True, width="stretch")
    if st.button("Clear chat", width="stretch"):
        st.session_state.messages = []
        st.rerun()

tab_chat, tab_arch = st.tabs(["💬 Chat", "🧭 Architecture"])

with tab_arch:
    st.markdown("""
**Flow:** user question → **Supervisor/Router** picks a specialist → specialist runs → **Reflection Agent** reviews
the output against the data it used → approved answers go to the user, rejected ones go back to the same specialist
with fix instructions (up to 2 correction rounds).
""")
    try:
        st.code(_graph().get_graph().draw_mermaid(), language="mermaid")
    except Exception as exc:  # pragma: no cover - visual aid only
        st.info(f"Graph diagram unavailable: {exc}")

with tab_chat:
    st.session_state.setdefault("messages", [])
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_result(msg["result"], key=f"m{i}")
            else:
                st.markdown(msg["content"])

    prompt = st.chat_input("Ask about providers, members, claims, files...") or st.session_state.pop("pending", None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        history = [{"role": m["role"], "content": m.get("content") or m["result"]["answer"]}
                   for m in st.session_state.messages[:-1]]
        with st.chat_message("assistant"):
            with st.spinner("Agents are working..."):
                try:
                    _graph()
                    result = ask(prompt, history)
                except Exception as exc:
                    result = {"answer": f"❌ Error: {exc}", "trace": [], "approved": False}
            render_result(result, key=f"m{len(st.session_state.messages)}")
        st.session_state.messages.append({"role": "assistant", "result": result})
