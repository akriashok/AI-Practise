"""Data Visualization Agent: charts validation pass/fail and core-layer outcomes for files per submitter."""
from __future__ import annotations

import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from healthcare_agents.agents.common import df_to_text, feedback_block, llm_text, records, trace_step
from healthcare_agents.agents.file_filters import extract_filters, where_clause
from healthcare_agents.db import query_df

USER_SQL = """
SELECT u.username, u.full_name, u.organization,
       COUNT(*) AS submitted,
       SUM(f.file_id IN (SELECT file_id FROM file_validation_results GROUP BY file_id HAVING SUM(result='FAIL')=0)) AS passed_validation,
       SUM(f.file_id IN (SELECT file_id FROM file_validation_results WHERE result='FAIL')) AS failed_validation,
       SUM(f.file_id IN (SELECT file_id FROM file_approvals WHERE decision='APPROVED')) AS approved,
       SUM(f.current_status='LOADED') AS reached_core
FROM file_submissions f JOIN submitter_users u ON u.user_id = f.submitted_by
{where} GROUP BY u.user_id ORDER BY submitted DESC"""

TREND_SQL = """
SELECT strftime('%Y-%m', f.submitted_at) AS month, COUNT(*) AS submitted,
       SUM(f.current_status='FAILED') AS failed_validation, SUM(f.current_status='LOADED') AS reached_core
FROM file_submissions f JOIN submitter_users u ON u.user_id = f.submitted_by {where} GROUP BY 1 ORDER BY 1"""

TYPE_SQL = """
SELECT f.file_type, f.current_status, COUNT(*) AS files
FROM file_submissions f JOIN submitter_users u ON u.user_id = f.submitted_by {where} GROUP BY 1,2"""

INSIGHT_SYSTEM = """You are a data visualization analyst for a healthcare file-ingestion platform.
The charts show, per submitting user, how many files passed or failed validation and how many reached the core layer.
Using ONLY the data provided, write 4-6 concise Markdown bullets of insights: best and worst submitters by
validation pass rate and core-load rate (give percentages), overall funnel conversion, notable trends, and one
recommendation. Never invent numbers; copy figures exactly from the data (use the TOTAL row for overall numbers).
The charts and the per-user table are already displayed to the user by the UI, so do NOT draw charts
(no mermaid/ASCII) and do NOT reproduce the full table."""


def build_charts(users, trend, types) -> list[go.Figure]:
    charts = []
    melted = users.melt(id_vars="username", value_vars=["passed_validation", "failed_validation", "reached_core"],
                        var_name="outcome", value_name="files")
    charts.append(px.bar(melted, x="username", y="files", color="outcome", barmode="group",
                         title="Validation outcome and core-layer loads by submitter",
                         color_discrete_map={"passed_validation": "#2ca02c", "failed_validation": "#d62728",
                                             "reached_core": "#1f77b4"}))
    totals = users[["submitted", "passed_validation", "approved", "reached_core"]].sum()
    charts.append(go.Figure(go.Funnel(y=["Submitted", "Passed validation", "Approved", "Reached core"],
                                      x=totals.tolist(), textinfo="value+percent initial"))
                  .update_layout(title="File pipeline funnel"))
    if len(trend) > 1:
        charts.append(px.line(trend, x="month", y=["submitted", "failed_validation", "reached_core"], markers=True,
                              title="Monthly submissions vs failures vs core loads"))
    if not types.empty:
        charts.append(px.bar(types, x="file_type", y="files", color="current_status", title="Current status by file type"))
    return charts


def visualization_node(state: dict) -> dict:
    started = time.time()
    filters = extract_filters(state["question"], state.get("history"))
    filters.update(statuses=[], stages=[], file_ids=[])
    where, params = where_clause(filters)
    users = query_df(USER_SQL.format(where=where), tuple(params))
    if users.empty:
        return {"answer": f"No file submissions match the filters {filters}.", "charts": [], "table": [], "error": None,
                "trace": [trace_step("data_visualization", started, filters=filters, charts=0)]}
    counts = ["submitted", "passed_validation", "failed_validation", "approved", "reached_core"]
    total = pd.DataFrame([{"username": "TOTAL", "full_name": "All submitters", "organization": "",
                           **users[counts].sum().to_dict()}])
    for df in (users, total):
        df["validation_pass_rate_pct"] = (100 * df["passed_validation"] / df["submitted"]).round(1)
        df["core_load_rate_pct"] = (100 * df["reached_core"] / df["submitted"]).round(1)
    trend = query_df(TREND_SQL.format(where=where), tuple(params))
    types = query_df(TYPE_SQL.format(where=where), tuple(params))
    charts = build_charts(users, trend, types)
    evidence = (f"Filters: {filters}\nCharts already rendered for the user by the UI: "
                f"{[c.layout.title.text for c in charts]}\nThe per-user table below is also displayed to the user.\n\n"
                f"Per-user outcomes:\n{df_to_text(pd.concat([users, total]))}\n\nMonthly trend:\n{df_to_text(trend)}")
    insights = llm_text(INSIGHT_SYSTEM, f"Request: {state['question']}\n{evidence}{feedback_block(state)}")
    return {
        "answer": insights,
        "evidence": evidence,
        "charts": [c.to_json() for c in charts],
        "table": records(users),
        "error": None,
        "trace": [trace_step("data_visualization", started, filters=filters, charts=len(charts))],
    }
