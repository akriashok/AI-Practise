# AI-Practise

Practice repo for working with Claude and the Model Context Protocol (MCP).

## Contents

- **[`mcp-agent/`](mcp-agent/)** — an MCP server exposing a few tools (time
  lookup, a safe calculator, a notes store) plus a Claude-powered agent that
  uses them via the standard agentic tool-call loop. See
  [`mcp-agent/README.md`](mcp-agent/README.md) for setup and usage.
- **`.mcp.json`** — registers the server so Claude Code picks up the same
  tools automatically when this repo is opened.
