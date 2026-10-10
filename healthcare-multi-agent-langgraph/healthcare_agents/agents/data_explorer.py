"""Data Explorer Agent: natural-language-to-SQL over the healthcare provider database."""
from __future__ import annotations

import re
import time

from healthcare_agents.agents.common import (df_to_text, feedback_block, history_text, llm_text, records,
                                             trace_step)
from healthcare_agents.db import run_select, schema_text

SQL_SYSTEM = """You are an expert healthcare data analyst who writes SQLite SQL.
Database schema (table(column TYPE -> referenced_table [sample values])):
{schema}

Rules:
- Write ONE read-only SQLite query (SELECT or WITH). Never modify data.
- Use only the tables/columns above. Join on the referenced keys.
- Use SQLite date functions (date(), strftime('%Y-%m', col)). Today's date is date('now'); data runs 2025-01-01 to 2026-09-30.
- Text values are case-sensitive; use the sample values shown, or UPPER()/LIKE for free text such as names.
- Give readable column aliases; ROUND money to 2 decimals; add ORDER BY for rankings.
- Return detail rows with LIMIT 50 unless the user asks for more.
Return only the SQL inside a ```sql code block."""

ANSWER_SYSTEM = """You are a healthcare data analyst. Answer the user's question using ONLY the SQL result provided.
Be concise (2-6 sentences or a short bullet list). Quote exact numbers from the result. If the result is empty,
say no matching records were found. Do not invent data."""


def _extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def data_explorer_node(state: dict) -> dict:
    started = time.time()
    question = state["question"]
    prompt = (f"Conversation so far:\n{history_text(state.get('history'))}\n\nQuestion: {question}"
              f"{feedback_block(state)}")
    if state.get("feedback") and state.get("sql"):
        prompt += f"\nPrevious SQL:\n{state['sql']}"
    system = SQL_SYSTEM.format(schema=schema_text())

    sql, df, error, attempts = "", None, None, 0
    for attempts in range(1, 4):
        sql = _extract_sql(llm_text(system, prompt, effort="medium"))
        try:
            df = run_select(sql)
            error = None
            if df.empty and attempts == 1:
                prompt += (f"\n\nYour SQL:\n{sql}\nreturned 0 rows. Verify every literal value (names, codes, statuses) "
                           "against the schema values listed; use LIKE for names. Return the same SQL if it is correct.")
                continue
            break
        except Exception as exc:
            error = str(exc)
            prompt += f"\n\nYour SQL:\n{sql}\nfailed with error: {error}\nReturn a corrected query."

    evidence = f"SQL result ({0 if df is None else len(df)} rows):\n{df_to_text(df)}"
    if error:
        answer = f"I could not produce a valid SQL query for this question. Last error: {error}"
    else:
        answer = llm_text(ANSWER_SYSTEM, f"Question: {question}\n\nSQL:\n{sql}\n\n{evidence}")
    return {
        "answer": answer,
        "evidence": evidence,
        "sql": sql,
        "table": records(df) if df is not None else [],
        "error": error,
        "trace": [trace_step("data_explorer", started, sql_attempts=attempts, rows=0 if df is None else len(df),
                             error=error)],
    }
