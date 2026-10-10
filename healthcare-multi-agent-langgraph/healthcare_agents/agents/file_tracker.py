"""File Tracker Agent: tracks submitted files through validation, approval and load stages."""
from __future__ import annotations

import time

from healthcare_agents.agents.common import df_to_text, feedback_block, llm_text, records, trace_step
from healthcare_agents.agents.file_filters import extract_filters, where_clause
from healthcare_agents.db import query_df

TRACKER_SYSTEM = """You are a file operations tracker for a healthcare data platform.
Pipeline: SUBMITTED -> VALIDATION (12 rules, PASS/FAIL) -> APPROVAL (APPROVED/REJECTED/PENDING) -> LOAD (LANDING -> STAGING -> CORE).
Using ONLY the data provided, answer the user's question. For a single file give a clear stage-by-stage timeline,
the current stage/status, failed validation rules with error counts, and the next action needed.
For multiple files summarise counts by status and call out files that are failed, rejected or stuck.
Use concise Markdown. Never invent file ids or numbers."""

FILE_SQL = """
SELECT f.file_id, f.file_name, f.file_type, u.username AS submitted_by, u.organization, f.submitted_at,
       f.record_count, f.current_stage, f.current_status, f.last_updated
FROM file_submissions f JOIN submitter_users u ON u.user_id = f.submitted_by
{where} ORDER BY f.submitted_at DESC LIMIT {limit}"""


def _file_detail(file_ids: list[str]) -> str:
    ph = ",".join("?" * len(file_ids))
    parts = {
        "Validation failures": query_df(
            f"SELECT v.file_id, v.rule_id, r.rule_description, r.severity, v.error_count, v.validated_at "
            f"FROM file_validation_results v JOIN validation_rules r USING(rule_id) WHERE v.file_id IN ({ph}) AND v.result='FAIL'", tuple(file_ids)),
        "Validation summary": query_df(
            f"SELECT file_id, SUM(result='PASS') AS rules_passed, SUM(result='FAIL') AS rules_failed, MAX(validated_at) AS validated_at "
            f"FROM file_validation_results WHERE file_id IN ({ph}) GROUP BY file_id", tuple(file_ids)),
        "Approval": query_df(f"SELECT file_id, decision, approver_name, decision_at, comments FROM file_approvals WHERE file_id IN ({ph})", tuple(file_ids)),
        "Load stages": query_df(
            f"SELECT file_id, stage_name, status, started_at, completed_at, records_loaded, records_rejected "
            f"FROM file_load_stages WHERE file_id IN ({ph}) ORDER BY file_id, stage_order", tuple(file_ids)),
    }
    return "\n\n".join(f"### {k}\n{df_to_text(v)}" for k, v in parts.items())


def file_tracker_node(state: dict) -> dict:
    started = time.time()
    filters = extract_filters(state["question"], state.get("history"))
    where, params = where_clause(filters)
    files = query_df(FILE_SQL.format(where=where, limit=200), tuple(params))
    status_counts = query_df(
        f"SELECT f.current_stage, f.current_status, COUNT(*) AS files FROM file_submissions f "
        f"JOIN submitter_users u ON u.user_id=f.submitted_by {where} GROUP BY 1,2 ORDER BY 3 DESC", tuple(params))
    context = f"Filters applied: {filters}\n\n### Status counts\n{df_to_text(status_counts)}\n\n### Files (most recent first, {len(files)} shown)\n{df_to_text(files, 25)}"
    if 0 < len(files) <= 5:
        context += "\n\n" + _file_detail(files["file_id"].tolist())
    elif len(files) > 5:
        ids = files["file_id"].tolist()
        ph = ",".join("?" * len(ids))
        per_file = query_df(
            f"SELECT file_id, GROUP_CONCAT(rule_id || ' (' || error_count || ' errors)', '; ') AS failed_rules "
            f"FROM file_validation_results WHERE result='FAIL' AND file_id IN ({ph}) GROUP BY file_id", tuple(ids))
        by_rule = query_df(
            f"SELECT v.rule_id, r.rule_description, r.severity, COUNT(*) AS files_failed, SUM(v.error_count) AS error_records "
            f"FROM file_validation_results v JOIN validation_rules r USING(rule_id) WHERE v.result='FAIL' AND v.file_id IN ({ph}) "
            f"GROUP BY 1,2,3 ORDER BY files_failed DESC", tuple(ids))
        context += (f"\n\n### Validation failures by rule (these files)\n{df_to_text(by_rule)}"
                    f"\n\n### Failed rules per file\n{df_to_text(per_file, 25)}")
    answer = llm_text(TRACKER_SYSTEM, f"Question: {state['question']}\n\n{context}{feedback_block(state)}")
    return {
        "answer": answer,
        "evidence": context,
        "table": records(files),
        "error": None,
        "trace": [trace_step("file_tracker", started, filters=filters, files_found=len(files))],
    }
