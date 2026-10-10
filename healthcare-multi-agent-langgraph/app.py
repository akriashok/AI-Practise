"""Gradio UI for the Healthcare Multi-Agent System (LangGraph)."""
from __future__ import annotations

import os

import gradio as gr
import pandas as pd
import plotly.io as pio

from healthcare_agents.db import ensure_db, table_counts
from healthcare_agents.graph import ask, build_graph

MAX_CHARTS = 4
AGENT_LABELS = {
    "router": "Supervisor / Router",
    "data_explorer": "Data Explorer Agent (NL2SQL)",
    "reporting": "Reporting Agent",
    "file_tracker": "File Tracker Agent",
    "data_visualization": "Data Visualization Agent",
    "reflection": "Reflection Agent",
}
EXAMPLES = [
    "How many active providers are there in each specialty?",
    "Top 10 members by total paid claims in 2026 with their plan name",
    "Which providers have credentials expiring in the next 90 days?",
    "Create an impact report on claim denials for the business review",
    "Give me an executive summary of the provider network",
    "Where is file FS-20250007 in the pipeline?",
    "Which files submitted by pkumar failed validation and why?",
    "Chart how many files each user passed or failed validation and reached core",
    "Visualize file outcomes for CLAIMS_837 files",
]


def _status(res: dict) -> str:
    badge = "✅ Approved by Reflection Agent" if res.get("approved") else "⚠️ Released after max review rounds"
    return (f"**Handled by:** {AGENT_LABELS.get(res.get('route'), res.get('route') or '-')}  \n"
            f"**Review:** {badge} (rounds: {res.get('reflection_count', 0)})")


def _empty_outputs():
    return ([gr.update(value=None, visible=False)] * MAX_CHARTS
            + [gr.update(value="", visible=False), gr.update(value=None, visible=False), None])


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("text") or ""
    if isinstance(content, (list, tuple)):
        return " ".join(_text(c) for c in content)
    return ""


def respond(message: str, history: list[dict]):
    message = (message or "").strip()
    if not message:
        yield history, "", gr.update(), *_empty_outputs()
        return
    agent_history = [{"role": m["role"], "content": _text(m["content"])} for m in history]
    history = history + [{"role": "user", "content": message},
                         {"role": "assistant", "content": "⏳ Agents are working..."}]
    yield history, "", "Routing question to the right agent...", *_empty_outputs()

    try:
        res = ask(message, agent_history)
    except Exception as exc:
        history[-1]["content"] = f"❌ Error: {exc}"
        yield history, "", "Error", *_empty_outputs()
        return

    history[-1]["content"] = res["answer"]
    charts = [pio.from_json(c) for c in (res.get("charts") or [])][:MAX_CHARTS]
    plots = [gr.update(value=charts[i], visible=True) if i < len(charts) else gr.update(value=None, visible=False)
             for i in range(MAX_CHARTS)]
    sql = gr.update(value=res.get("sql") or "", visible=bool(res.get("sql")))
    table = gr.update(value=pd.DataFrame(res["table"]), visible=True) if res.get("table") else gr.update(value=None, visible=False)
    trace = [{"agent": AGENT_LABELS.get(s["agent"], s["agent"]), **{k: v for k, v in s.items() if k != "agent"}}
             for s in res.get("trace", [])]
    yield history, "", _status(res), *plots, sql, table, trace


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Healthcare Multi-Agent System") as demo:
        gr.Markdown("# 🩺 Healthcare Multi-Agent System\n"
                    "LangGraph · LangChain · SQLite (40 tables) · OpenRouter LLM — agents: **Data Explorer (NL2SQL)**, "
                    "**Reporting**, **File Tracker**, **Data Visualization**, **Reflection**")
        with gr.Tab("💬 Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(height=560, label="Conversation", buttons=["copy"])
                    with gr.Row():
                        box = gr.Textbox(placeholder="Ask about providers, members, claims, files...", show_label=False,
                                         scale=5, autofocus=True)
                        send = gr.Button("Send", variant="primary", scale=1)
                    gr.Examples(EXAMPLES, inputs=box, label="Example questions")
                    clear = gr.Button("Clear chat")
                with gr.Column(scale=2):
                    status = gr.Markdown("Ask a question to start.")
                    plots = [gr.Plot(visible=False, show_label=False) for _ in range(MAX_CHARTS)]
                    sql = gr.Code(language="sql", label="Generated SQL", visible=False)
                    table = gr.Dataframe(label="Result data", visible=False, wrap=True, max_height=400)
                    with gr.Accordion("Agent trace", open=False):
                        trace = gr.JSON(label="Steps")
            outputs = [chatbot, box, status, *plots, sql, table, trace]
            box.submit(respond, [box, chatbot], outputs)
            send.click(respond, [box, chatbot], outputs)
            clear.click(lambda: ([], "", "Ask a question to start.", *_empty_outputs()), None, outputs)

        with gr.Tab("🧭 Architecture"):
            gr.Markdown("**Flow:** user question → **Supervisor/Router** picks a specialist → specialist runs → "
                        "**Reflection Agent** reviews the output against the data it used → approved answers go to the "
                        "user; rejected ones go back to the same specialist with fix instructions (up to 2 rounds).\n\n"
                        f"```mermaid\n{build_graph().get_graph().draw_mermaid()}\n```")

        with gr.Tab("🗄️ Database"):
            gr.Markdown("Synthetic healthcare database: provider, member/plan, clinical, claims and file-operations domains.")
            gr.Dataframe(table_counts(), label="40 tables", max_height=700)
    return demo


if __name__ == "__main__":
    ensure_db()
    build_ui().queue(default_concurrency_limit=4).launch(
        server_name=os.environ.get("HOST", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", "7860")),
        theme=gr.themes.Soft(),
        ssr_mode=False,
    )
