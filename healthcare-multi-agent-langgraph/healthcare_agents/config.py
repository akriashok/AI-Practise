"""Paths, environment loading and the shared LLM client (OpenRouter via ChatOpenAI)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _f in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".venv", PROJECT_ROOT / ".venv"):
    if _f.is_file():
        load_dotenv(_f)

DB_PATH = Path(os.environ.get("HEALTHCARE_DB_PATH", PROJECT_ROOT / "data" / "healthcare.db"))
MAX_REFLECTIONS = int(os.environ.get("MAX_REFLECTIONS", "2"))


@lru_cache(maxsize=8)
def get_llm(temperature: float = 0.0, effort: str = "low"):
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to .env or the hosting provider's environment.")
    return ChatOpenAI(
        model=os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b"),
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=api_key,
        temperature=temperature,
        timeout=90,
        max_retries=2,
        extra_body={"reasoning": {"effort": effort}},
    )
