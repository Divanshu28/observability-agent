import os
import json
from typing import Optional
from openai import AzureOpenAI
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class ObservabilityAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.tools: list = []
        self.mcp_session: Optional[ClientSession] = None
        self._read = None
        self._write = None
        self._mcp_context = None

    async def connect(self):
        """Connect to DataDog MCP server and load available tools."""
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@datadog/mcp-datadog"],
            env={
                "DD_API_KEY": os.getenv("DD_API_KEY"),
                "DD_APP_KEY": os.getenv("DD_APP_KEY"),
                "DD_SITE": os.getenv("DD_SITE", "datadoghq.com")
            }
        )

        self._mcp_context = stdio_client(server_params)
        self._read, self._write = await self._mcp_context.__aenter__()
        self.mcp_session = ClientSession(self._read, self._write)
        await self.mcp_session.__aenter__()
        await self.mcp_session.initialize()

        tools_response = await self.mcp_session.list_tools()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            }
            for t in tools_response.tools
        ]
        print(f"[agent] Connected to DataDog MCP — {len(self.tools)} tools loaded")

    async def disconnect(self):
        if self.mcp_session:
            await self.mcp_session.__aexit__(None, None, None)
        if self._mcp_context:
            await self._mcp_context.__aexit__(None, None, None)

    async def _call_tool(self, name: str, arguments: dict) -> str:
        result = await self.mcp_session.call_tool(name, arguments)
        parts = [c.text if hasattr(c, "text") else str(c) for c in result.content]
        return json.dumps(parts)

    async def chat(self, history: list, user_message: str) -> tuple[str, list]:
        """
        Run one turn of the agent loop.
        Returns (assistant_response, updated_history).
        Loops internally until the model stops making tool calls.
        """
        history.append({"role": "user", "content": user_message})

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=history,
                tools=self.tools or None,
                tool_choice="auto" if self.tools else None,
                temperature=0
            )
            msg = response.choices[0].message

            # No tool calls — model has a final answer
            if not msg.tool_calls:
                content = msg.content or ""
                history.append({"role": "assistant", "content": content})
                return content, history

            # Append assistant message with its tool call requests
            history.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
            })

            # Execute each tool and feed results back
            for tc in msg.tool_calls:
                print(f"[agent] Calling tool: {tc.function.name}")
                result = await self._call_tool(
                    tc.function.name,
                    json.loads(tc.function.arguments)
                )
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })
            # Loop — model sees tool results and either answers or calls more tools
