"""SQLite access helpers: read-only query execution and schema description for the LLM."""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache

import pandas as pd

from healthcare_agents.config import DB_PATH
from healthcare_agents.seed_data import build_database

_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex)\b", re.I)


def ensure_db() -> None:
    build_database(DB_PATH)


def _connect() -> sqlite3.Connection:
    ensure_db()
    return sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, check_same_thread=False)


def query_df(sql: str, params: tuple | dict = ()) -> pd.DataFrame:
    with _connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def validate_select(sql: str) -> str:
    """Allow only a single read-only SELECT/WITH statement."""
    cleaned = sql.strip().rstrip(";").strip()
    if ";" in cleaned:
        raise ValueError("Only a single SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if _FORBIDDEN.search(cleaned):
        raise ValueError("Query contains a forbidden keyword.")
    return cleaned


def run_select(sql: str, max_rows: int = 500) -> pd.DataFrame:
    cleaned = validate_select(sql)
    return query_df(f"SELECT * FROM (\n{cleaned}\n) LIMIT {max_rows}")


@lru_cache(maxsize=1)
def table_names() -> list[str]:
    return query_df("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")["name"].tolist()


@lru_cache(maxsize=1)
def schema_text() -> str:
    """Compact schema with columns, FKs and sample categorical values to ground NL2SQL."""
    lines = []
    with _connect() as con:
        for t in table_names():
            cols = con.execute(f"PRAGMA table_info({t})").fetchall()
            fks = {f[3]: f"{f[2]}" for f in con.execute(f"PRAGMA foreign_key_list({t})").fetchall()}
            parts = []
            for _, name, ctype, *_ in cols:
                hint = f" -> {fks[name]}" if name in fks else ""
                if ctype == "TEXT" and re.search(r"(status|type|stage|category|decision|result|tier|gender|flag|role|severity|line_of_business|urgency|method)$", name):
                    vals = [v for (v,) in con.execute(f"SELECT DISTINCT {name} FROM {t} WHERE {name} IS NOT NULL LIMIT 8")]
                    hint += f" {vals}"
                parts.append(f"{name} {ctype}{hint}")
            lines.append(f"{t}({', '.join(parts)})")
            name_cols = [c[1] for c in cols if re.search(r"(_name|description)$", c[1])]
            if name_cols and con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] <= 25:
                vals = [v for (v,) in con.execute(f"SELECT {name_cols[0]} FROM {t}")]
                lines.append(f"  -- {t}.{name_cols[0]} values: {vals}")
    return "\n".join(lines)


def table_counts() -> pd.DataFrame:
    with _connect() as con:
        rows = [(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in table_names()]
    return pd.DataFrame(rows, columns=["table", "rows"])
