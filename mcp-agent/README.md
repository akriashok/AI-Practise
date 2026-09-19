# MCP Tool-Using Agent

A small, self-contained example of the MCP (Model Context Protocol) pattern:

- **`server.py`** — an MCP server (built with `FastMCP`) exposing five tools:
  `get_time`, `calculate`, `add_note`, `list_notes`, `search_notes`.
- **`agent.py`** — a Claude-powered agent that connects to the server over
  stdio, lists its tools, and runs the agentic tool-call loop (ask Claude →
  Claude requests a tool → run it via MCP → feed the result back → repeat
  until Claude gives a final answer).

## Setup

```bash
cd mcp-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run the agent

```bash
python agent.py "What's 12 * (7 + 5)? Save the answer as a note called 'math'."
python agent.py "What notes do I have?"
python agent.py "What time is it in Tokyo right now?"
```

The agent spawns `server.py` itself as a subprocess (stdio transport) — you
don't need to run the server separately.

## Use the server directly in Claude Code / Claude Desktop

This repo's `.mcp.json` (at the repo root) already registers the server as
`practice-tools`, so opening this repo in Claude Code gives Claude access to
the same tools directly, no separate agent script needed.

To add it to Claude Desktop instead, add to its config
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "practice-tools": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-agent/server.py"]
    }
  }
}
```

## Notes

- `calculate` only evaluates arithmetic (`+ - * / % **`) via an AST
  allow-list — no `eval()`, no arbitrary code execution.
- Notes are stored in `mcp-agent/notes.json`, created on first `add_note`
  call and git-ignored.
