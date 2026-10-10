"""Helpers shared by all agents: LLM calls, JSON parsing, data formatting."""
from __future__ import annotations

import json
import re
import time
from typing import Any

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from healthcare_agents.config import get_llm


def llm_text(system: str, user: str, temperature: float = 0.0, effort: str = "low") -> str:
    resp = get_llm(temperature, effort).invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return re.sub(r"<think>.*?</think>", "", str(resp.content), flags=re.S).strip()


def llm_json(system: str, user: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    text = llm_text(system + "\nRespond with a single JSON object only, no prose, no code fences.", user)
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return dict(default or {})


def df_to_text(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df is None or df.empty:
        return "(no rows)"
    extra = f"\n... {len(df) - max_rows} more rows" if len(df) > max_rows else ""
    return df.head(max_rows).to_csv(index=False) + extra


def records(df: pd.DataFrame, max_rows: int = 500) -> list[dict[str, Any]]:
    return json.loads(df.head(max_rows).to_json(orient="records", date_format="iso")) if df is not None else []


def history_text(history: list[dict[str, str]] | None, turns: int = 6) -> str:
    if not history:
        return "(none)"
    return "\n".join(f"{m['role']}: {m['content'][:500]}" for m in history[-turns:])


def trace_step(agent: str, started: float, **details: Any) -> dict[str, Any]:
    return {"agent": agent, "seconds": round(time.time() - started, 2), **details}


def feedback_block(state: dict) -> str:
    if not state.get("feedback"):
        return ""
    return (f"\n\nA reviewer rejected your previous answer. Fix these issues:\n{state['feedback']}"
            f"\nPrevious answer:\n{state.get('answer', '')[:1500]}")
