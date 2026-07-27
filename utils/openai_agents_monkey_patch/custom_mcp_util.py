# monkeypatch
from __future__ import annotations
from agents.mcp.util import *
from agents import _debug
import json
import os
from typing import Any
from utils.general.helper import print_color
from utils.openai_agents_monkey_patch.tool_name_aliases import (
    to_model_mcp_tool_name,
)


import shortuuid

MAX_SINGLE_TURN_RETURN_CHARS = int(os.getenv("BENCH_MAX_SINGLE_TURN_RETURN_CHARS", 100000)) # Maximum number of characters allowed in a single turn tool return
ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT = os.getenv("BENCH_ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT", "true").lower() == "true"

print_color(f"BENCH_ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT: {ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT} | MAX_SINGLE_TURN_RETURN_CHARS: {MAX_SINGLE_TURN_RETURN_CHARS}", color="blue")


_JSON_COERCIBLE_SCHEMA_TYPES = {"object", "array", "integer", "number", "boolean"}


def _declared_schema_types(schema: dict[str, Any]) -> set[str]:
    """Return all explicit JSON types declared by a schema or its unions."""
    declared: set[str] = set()
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        declared.add(schema_type)
    elif isinstance(schema_type, list):
        declared.update(item for item in schema_type if isinstance(item, str))

    for union_key in ("anyOf", "oneOf"):
        for option in schema.get(union_key, []):
            if isinstance(option, dict):
                declared.update(_declared_schema_types(option))
    return declared


def _value_matches_schema_type(value: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "null":
        return value is None
    return False


def _matching_schema(value: Any, schema: dict[str, Any]) -> dict[str, Any]:
    """Pick the union branch that matches value, falling back to schema."""
    for union_key in ("anyOf", "oneOf"):
        for option in schema.get(union_key, []):
            if not isinstance(option, dict):
                continue
            if any(
                _value_matches_schema_type(value, declared_type)
                for declared_type in _declared_schema_types(option)
            ):
                return option
    return schema


def _coerce_stringified_json_value(value: Any, schema: dict[str, Any]) -> Any:
    """Repair JSON-stringified values only when their schema requires it."""
    if not isinstance(schema, dict):
        return value

    declared_types = _declared_schema_types(schema)
    coercible_types = declared_types & _JSON_COERCIBLE_SCHEMA_TYPES
    if isinstance(value, str) and coercible_types and "string" not in declared_types:
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError):
            decoded = value

        if any(
            _value_matches_schema_type(decoded, schema_type)
            for schema_type in coercible_types
        ):
            value = decoded

    active_schema = _matching_schema(value, schema)
    if isinstance(value, dict):
        properties = active_schema.get("properties", {})
        additional_properties = active_schema.get("additionalProperties")
        return {
            key: _coerce_stringified_json_value(
                item,
                properties.get(key)
                if isinstance(properties.get(key), dict)
                else additional_properties
                if isinstance(additional_properties, dict)
                else {},
            )
            for key, item in value.items()
        }
    if isinstance(value, list) and isinstance(active_schema.get("items"), dict):
        return [
            _coerce_stringified_json_value(item, active_schema["items"])
            for item in value
        ]
    return value


def coerce_mcp_arguments(
    arguments: dict[str, Any], input_schema: dict[str, Any]
) -> dict[str, Any]:
    """Coerce provider-stringified MCP arguments according to the tool schema."""
    coerced = _coerce_stringified_json_value(arguments, input_schema)
    return coerced if isinstance(coerced, dict) else arguments


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
        # Only the model-facing alias is normalized. The callback above keeps
        # the original server/tool objects for the real MCP call.
        name=to_model_mcp_tool_name(server.name, tool.name),
        description=tool.description or "",
        params_json_schema=schema,
        on_invoke_tool=invoke_func,
        strict_json_schema=is_strict,
    )


@classmethod
async def my_invoke_mcp_tool(
    cls, server: "MCPServer", tool: "MCPTool", context: RunContextWrapper[Any], input_json: str
) -> str:
    """Invoke an MCP tool and return the result as a string."""
    try:
        json_data: dict[str, Any] = json.loads(input_json) if input_json else {}
    except Exception as e:
        if _debug.DONT_LOG_TOOL_DATA:
            logger.debug(f"Invalid JSON input for tool {tool.name}")
        else:
            logger.debug(f"Invalid JSON input for tool {tool.name}: {input_json}")
        raise ModelBehaviorError(
            f"Invalid JSON input for tool {tool.name}: {input_json}"
        ) from e

    json_data = coerce_mcp_arguments(json_data, tool.inputSchema)

    if _debug.DONT_LOG_TOOL_DATA:
        logger.debug(f"Invoking MCP tool {tool.name}")
    else:
        logger.debug(f"Invoking MCP tool {tool.name} with input {input_json}")

    try:
        result = await server.call_tool(tool.name, json_data)
    except Exception as e:
        logger.error(f"Error invoking MCP tool {tool.name}: {e}")
        raise AgentsException(f"Error invoking MCP tool {tool.name}: {e}") from e

    if _debug.DONT_LOG_TOOL_DATA:
        logger.debug(f"MCP tool {tool.name} completed.")
    else:
        logger.debug(f"MCP tool {tool.name} returned {result}")

    # The MCP tool result is a list of content items, whereas OpenAI tool outputs are a single
    # string. We'll try to convert.
    if len(result.content) == 1:
        tool_output = result.content[0].model_dump_json()
    elif len(result.content) > 1:
        tool_output = json.dumps([item.model_dump() for item in result.content])
    else:
        # logger.error(f"Errored MCP tool result: {result}")
        tool_output = "[]" # Returning empty is a reasonable value

    current_span = get_current_span()
    if current_span:
        if isinstance(current_span.span_data, FunctionSpanData):
            current_span.span_data.output = tool_output
            current_span.span_data.mcp_data = {
                "server": server.name,
            }
        else:
            logger.warning(
                f"Current span is not a FunctionSpanData, skipping tool output: {current_span}"
            )

    # this is a very temp solution!
    if len(tool_output) > MAX_SINGLE_TURN_RETURN_CHARS:
        original_length = len(tool_output)

        logger.warning(f"Tool output is too long, return truncated one.")
        tool_short_uuid = shortuuid.uuid()

        agent_workspace = context.context.get('_agent_workspace', '.')
        agent_workspace = os.path.abspath(agent_workspace)
        overlong_toolcall_save_dir = os.path.join(agent_workspace, '.overlong_tool_outputs')
        os.makedirs(overlong_toolcall_save_dir, exist_ok=True)

        # save the original tool output to a file
        with open(os.path.join(overlong_toolcall_save_dir, f"{tool_short_uuid}.json"), "w", encoding="utf-8") as f:
            f.write(tool_output)
        logger.warning(f"Tool output saved to {os.path.join(overlong_toolcall_save_dir, f'{tool_short_uuid}.json')}")
        
        tool_output = tool_output[:MAX_SINGLE_TURN_RETURN_CHARS] + \
            f" ...\n\n(The output of the tool call (shortuuid identifier: {tool_short_uuid}) is too long! Only the first {MAX_SINGLE_TURN_RETURN_CHARS} characters are shown here. The original output length is {original_length} characters. The full output has been saved to the file {os.path.join(overlong_toolcall_save_dir, f'{tool_short_uuid}.json')}. Please check this file carefully, as it may be very long!)"

    return tool_output

# Replace method
MCPUtil.invoke_mcp_tool = my_invoke_mcp_tool
# Must replace the one above first
MCPUtil.to_function_tool = my_to_function_tool
