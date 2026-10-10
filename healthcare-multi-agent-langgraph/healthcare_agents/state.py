"""Shared LangGraph state passed between agents."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    history: list[dict[str, str]]
    route: str
    route_reason: str
    answer: str
    sql: str | None
    table: list[dict[str, Any]]
    charts: list[str]
    evidence: str
    error: str | None
    feedback: str | None
    reflection_count: int
    approved: bool
    trace: Annotated[list[dict[str, Any]], operator.add]
