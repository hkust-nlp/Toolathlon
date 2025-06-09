# monkeypatch
from __future__ import annotations
from agents.mcp.util import *


@classmethod
def my_to_function_tool(
    cls, tool: "MCPTool", server: "MCPServer", convert_schemas_to_strict: bool
) -> FunctionTool:
    """Convert an MCP tool to an Agents SDK function tool."""
    invoke_func = functools.partial(cls.invoke_mcp_tool, server, tool)
    schema, is_strict = tool.inputSchema, False

    # MCP spec doesn't require the inputSchema to have `properties`, but OpenAI spec does.
    if "properties" not in schema:
        schema["properties"] = {}

    if convert_schemas_to_strict:
        try:
            schema = ensure_strict_json_schema(schema)
            is_strict = True
        except Exception as e:
            logger.info(f"Error converting MCP schema to strict mode: {e}")

    return FunctionTool(
        name=server.name
        + "-"
        + tool.name,  # add the server name as prefix to distinguish duplicate tool names
        description=tool.description or "",
        params_json_schema=schema,
        on_invoke_tool=invoke_func,
        strict_json_schema=is_strict,
    )

# 替换方法
MCPUtil.to_function_tool = my_to_function_tool