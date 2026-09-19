"""A minimal tool-using agent: connects to the local MCP server (server.py)
over stdio, hands its tools to Claude, and runs the agentic tool-call loop
until Claude produces a final answer.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py "What's 12 * (7 + 5)? Save the answer as a note called 'math'."
"""
import asyncio
import sys

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "claude-sonnet-5"


def mcp_tools_to_anthropic(tools):
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        for t in tools
    ]


async def run_agent(user_prompt: str) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=["server.py"])
    client = Anthropic()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = mcp_tools_to_anthropic(tools_result.tools)

            messages = [{"role": "user", "content": user_prompt}]

            while True:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    tools=tools,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    return "".join(
                        block.text for block in response.content if block.type == "text"
                    )

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    result = await session.call_tool(block.name, block.input)
                    text = "".join(
                        c.text for c in result.content if getattr(c, "type", None) == "text"
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": text,
                            "is_error": result.isError,
                        }
                    )
                messages.append({"role": "user", "content": tool_results})


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py \"<prompt>\"")
        sys.exit(1)
    prompt = " ".join(sys.argv[1:])
    answer = asyncio.run(run_agent(prompt))
    print(answer)


if __name__ == "__main__":
    main()
