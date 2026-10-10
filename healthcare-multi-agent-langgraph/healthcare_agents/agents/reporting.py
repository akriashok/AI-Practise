"""Reporting Agent: builds summary and impact reports for business review from curated KPI queries."""
from __future__ import annotations

import re
import time

from healthcare_agents.agents.common import df_to_text, feedback_block, llm_text, trace_step
from healthcare_agents.db import query_df

KPI_QUERIES: dict[str, dict[str, str]] = {
    "claims": {
        "Claims overview": """
            SELECT COUNT(*) AS total_claims, ROUND(SUM(billed_amount),2) AS billed, ROUND(SUM(allowed_amount),2) AS allowed,
                   ROUND(SUM(paid_amount),2) AS paid, ROUND(100.0*SUM(claim_status='DENIED')/COUNT(*),2) AS denial_rate_pct,
                   ROUND(AVG(julianday(adjudicated_date)-julianday(received_date)),1) AS avg_days_to_adjudicate
            FROM claims""",
        "Claims by status": "SELECT claim_status, COUNT(*) AS claims, ROUND(SUM(paid_amount),2) AS paid FROM claims GROUP BY 1 ORDER BY 2 DESC",
        "Monthly claims trend (last 6 months)": """
            SELECT strftime('%Y-%m', service_date) AS month, COUNT(*) AS claims, ROUND(SUM(paid_amount),2) AS paid,
                   ROUND(100.0*SUM(claim_status='DENIED')/COUNT(*),2) AS denial_rate_pct
            FROM claims GROUP BY 1 ORDER BY 1 DESC LIMIT 6""",
        "Top denial reasons": """
            SELECT d.denial_code, r.description, r.category, COUNT(*) AS denials, ROUND(SUM(c.billed_amount),2) AS billed_at_risk,
                   SUM(d.appealed) AS appealed, SUM(d.appeal_outcome='OVERTURNED') AS overturned
            FROM claim_denials d JOIN denial_reasons r USING(denial_code) JOIN claims c USING(claim_id)
            GROUP BY 1,2,3 ORDER BY denials DESC LIMIT 6""",
        "Paid by line of business": """
            SELECT p.line_of_business, COUNT(*) AS claims, ROUND(SUM(c.paid_amount),2) AS paid,
                   ROUND(SUM(c.paid_amount)*1.0/COUNT(DISTINCT c.member_id),2) AS paid_per_member
            FROM claims c JOIN health_plans p USING(plan_id) GROUP BY 1 ORDER BY paid DESC""",
    },
    "provider": {
        "Provider network overview": """
            SELECT COUNT(*) AS providers, SUM(status='ACTIVE') AS active, SUM(status='PENDING') AS pending,
                   SUM(status='TERMINATED') AS terminated, SUM(accepting_new_patients) AS accepting_new_patients FROM providers""",
        "Active providers by specialty": """
            SELECT s.specialty_name, COUNT(*) AS providers FROM providers p JOIN specialties s ON s.specialty_id=p.primary_specialty_id
            WHERE p.status='ACTIVE' GROUP BY 1 ORDER BY 2 DESC""",
        "Credentials expiring in next 90 days or expired": """
            SELECT credential_type, SUM(expiration_date < date('now')) AS expired,
                   SUM(expiration_date BETWEEN date('now') AND date('now','+90 day')) AS expiring_90_days
            FROM provider_credentials GROUP BY 1""",
        "Network participation": """
            SELECT n.network_name, SUM(pnp.status='ACTIVE') AS active_providers, SUM(pnp.status='TERMINATED') AS terminated
            FROM provider_network_participation pnp JOIN networks n USING(network_id) GROUP BY 1 ORDER BY 2 DESC""",
        "Top providers by paid amount": """
            SELECT p.first_name||' '||p.last_name AS provider, s.specialty_name, COUNT(c.claim_id) AS claims, ROUND(SUM(c.paid_amount),2) AS paid
            FROM claims c JOIN providers p USING(provider_id) JOIN specialties s ON s.specialty_id=p.primary_specialty_id
            GROUP BY c.provider_id ORDER BY paid DESC LIMIT 5""",
    },
    "files": {
        "File pipeline overview": """
            SELECT COUNT(*) AS files_submitted, SUM(current_status='LOADED') AS reached_core,
                   SUM(current_status='FAILED') AS failed_validation, SUM(current_status IN ('PENDING_APPROVAL','IN_PROGRESS')) AS in_flight,
                   SUM(current_status='REJECTED') AS rejected, SUM(current_status='LOAD_FAILED') AS load_failed,
                   ROUND(100.0*SUM(current_status='LOADED')/COUNT(*),2) AS core_success_rate_pct FROM file_submissions""",
        "Files by type": """
            SELECT file_type, COUNT(*) AS files, SUM(current_status='LOADED') AS loaded, SUM(current_status='FAILED') AS failed_validation
            FROM file_submissions GROUP BY 1 ORDER BY 2 DESC""",
        "Most frequent validation failures": """
            SELECT v.rule_id, r.rule_description, r.severity, COUNT(*) AS failures, SUM(v.error_count) AS error_records
            FROM file_validation_results v JOIN validation_rules r USING(rule_id) WHERE v.result='FAIL'
            GROUP BY 1,2,3 ORDER BY failures DESC LIMIT 6""",
        "Records rejected during load": """
            SELECT stage_name, COUNT(*) AS runs, SUM(status='FAILED') AS failed_runs, SUM(records_loaded) AS loaded, SUM(records_rejected) AS rejected
            FROM file_load_stages GROUP BY 1 ORDER BY MIN(stage_order)""",
    },
}

REPORT_SYSTEM = """You are a healthcare business analyst preparing a report for a business review meeting.
Use ONLY the KPI data provided. Write in Markdown with these sections:
## Executive Summary  (3-4 bullets)
## Key Metrics  (a compact markdown table of the most important figures)
## Impact Analysis  (financial / operational / member or provider impact, quantified with the given numbers)
## Risks & Issues
## Recommendations  (3-5 concrete actions)
Keep it under 450 words. Never invent numbers; format money as $1,234,567."""


def _scope(question: str) -> list[str]:
    q = question.lower()
    picked = [k for k, pat in (("claims", r"claim|denial|payment|paid|financ|cost|reimburs"),
                               ("provider", r"provider|network|credential|specialt|physician|contract"),
                               ("files", r"file|submission|validation|load|pipeline|ingest|approval"))
              if re.search(pat, q)]
    return picked or list(KPI_QUERIES)


def reporting_node(state: dict) -> dict:
    started = time.time()
    scopes = _scope(state["question"])
    sections, kpi_rows = [], []
    for scope in scopes:
        for title, sql in KPI_QUERIES[scope].items():
            df = query_df(sql)
            sections.append(f"### {title}\n{df_to_text(df, 20)}")
            if len(df) == 1:
                kpi_rows += [{"area": scope, "metric": k, "value": v} for k, v in df.iloc[0].items()]
    evidence = "KPI data:\n" + "\n\n".join(sections)
    report = llm_text(REPORT_SYSTEM, f"Report request: {state['question']}\nScope: {', '.join(scopes)}\n\n{evidence}"
                      + feedback_block(state), temperature=0.2)
    return {
        "answer": report,
        "evidence": evidence,
        "table": kpi_rows,
        "error": None,
        "trace": [trace_step("reporting", started, scopes=scopes, kpi_queries=len(sections))],
    }
