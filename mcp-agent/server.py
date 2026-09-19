"""MCP server exposing a small set of tools: time lookup, a safe calculator,
and a simple notes store. Run directly (stdio transport) or point an MCP
client (Claude Desktop, Claude Code, agent.py in this folder) at it.
"""
import ast
import json
import operator
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("practice-agent-tools")

NOTES_PATH = os.path.join(os.path.dirname(__file__), "notes.json")

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def _load_notes():
    if not os.path.exists(NOTES_PATH):
        return []
    with open(NOTES_PATH, "r") as f:
        return json.load(f)


def _save_notes(notes):
    with open(NOTES_PATH, "w") as f:
        json.dump(notes, f, indent=2)


@mcp.tool()
def get_time(timezone: str = "UTC") -> str:
    """Get the current date and time in a given IANA timezone (e.g. 'UTC', 'America/New_York')."""
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return f"Unknown timezone: {timezone}"
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a basic arithmetic expression (+, -, *, /, %, **). No variables or function calls."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def add_note(title: str, content: str) -> str:
    """Save a note with a title and content."""
    notes = _load_notes()
    notes.append({"title": title, "content": content, "created": datetime.utcnow().isoformat()})
    _save_notes(notes)
    return f"Saved note '{title}' ({len(notes)} total notes)."


@mcp.tool()
def list_notes() -> str:
    """List all saved notes."""
    notes = _load_notes()
    if not notes:
        return "No notes saved yet."
    return "\n".join(f"- {n['title']}: {n['content']}" for n in notes)


@mcp.tool()
def search_notes(query: str) -> str:
    """Search saved notes by title or content substring (case-insensitive)."""
    query_lower = query.lower()
    matches = [
        n for n in _load_notes()
        if query_lower in n["title"].lower() or query_lower in n["content"].lower()
    ]
    if not matches:
        return f"No notes match '{query}'."
    return "\n".join(f"- {n['title']}: {n['content']}" for n in matches)


if __name__ == "__main__":
    mcp.run()
