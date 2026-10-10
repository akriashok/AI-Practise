"""Extract file-operation filters (file ids, submitters, statuses, types, dates) from a question."""
from __future__ import annotations

import re
from functools import lru_cache

from healthcare_agents.agents.common import history_text, llm_json
from healthcare_agents.db import query_df

STATUSES = ["IN_PROGRESS", "FAILED", "PENDING_APPROVAL", "REJECTED", "LOAD_FAILED", "LOADED"]
STAGES = ["VALIDATION", "APPROVAL", "LOAD", "LANDING", "STAGING", "CORE"]


@lru_cache(maxsize=1)
def _lookup():
    users = query_df("SELECT user_id, username, full_name, organization FROM submitter_users")
    types = query_df("SELECT DISTINCT file_type FROM file_submissions")["file_type"].tolist()
    return users, types


def extract_filters(question: str, history: list | None = None) -> dict:
    users, types = _lookup()
    filters = llm_json(
        "Extract filters for querying healthcare file submissions.\n"
        f"Allowed usernames: {users[['username', 'full_name', 'organization']].to_dict('records')}\n"
        f"Allowed statuses: {STATUSES} (FAILED = failed validation, LOADED = reached core layer)\n"
        f"Allowed stages: {STAGES}\nAllowed file types: {types}\n"
        'Return {"file_ids": [], "usernames": [], "statuses": [], "stages": [], "file_types": [], '
        '"date_from": "YYYY-MM-DD or null", "date_to": "YYYY-MM-DD or null"}. Use empty lists when not mentioned. '
        "Data spans 2025-06-01 to 2026-09-30; resolve relative dates against 2026-09-30.",
        f"Conversation so far:\n{history_text(history)}\n\nQuestion: {question}",
        default={},
    )
    ids = set(filters.get("file_ids") or []) | {m.upper() for m in re.findall(r"FS-\d{8}", question, re.I)}
    names = set(filters.get("usernames") or [])
    q = question.lower()
    for _, u in users.iterrows():
        if u["username"] in q or u["full_name"].lower() in q:
            names.add(u["username"])
    file_ids = sorted(i for i in ids if re.fullmatch(r"FS-\d{8}", i))
    if file_ids:
        return {"file_ids": file_ids, "usernames": [], "statuses": [], "stages": [], "file_types": [],
                "date_from": None, "date_to": None}
    return {
        "file_ids": [],
        "usernames": sorted(n for n in names if n in set(users["username"])),
        "statuses": [s for s in filters.get("statuses") or [] if s in STATUSES],
        "stages": [s for s in filters.get("stages") or [] if s in STAGES],
        "file_types": [t for t in filters.get("file_types") or [] if t in types],
        "date_from": filters.get("date_from") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(filters.get("date_from"))) else None,
        "date_to": filters.get("date_to") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(filters.get("date_to"))) else None,
    }


def where_clause(f: dict, alias: str = "f") -> tuple[str, list]:
    clauses, params = [], []
    for key, col in (("file_ids", "file_id"), ("statuses", "current_status"), ("stages", "current_stage"),
                     ("file_types", "file_type")):
        if f.get(key):
            clauses.append(f"{alias}.{col} IN ({','.join('?' * len(f[key]))})")
            params += f[key]
    if f.get("usernames"):
        clauses.append(f"u.username IN ({','.join('?' * len(f['usernames']))})")
        params += f["usernames"]
    if f.get("date_from"):
        clauses.append(f"date({alias}.submitted_at) >= ?")
        params.append(f["date_from"])
    if f.get("date_to"):
        clauses.append(f"date({alias}.submitted_at) <= ?")
        params.append(f["date_to"])
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", params
