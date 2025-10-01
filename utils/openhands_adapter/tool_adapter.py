"""
OpenHands Tool Adapter

将 OpenAI Agents SDK 的 FunctionTool 转换为 OpenHands SDK 的 Tool 格式
"""

from typing import Any, Dict, Callable
from openhands.sdk.tool import Tool, ToolSpec, register_tool
from openhands.sdk.tool.schema import Action, Observation


def convert_function_tool_to_openhands(function_tool) -> Tool:
    """
    将 FunctionTool (OpenAI Agents SDK) 转换为 OpenHands Tool

    Args:
        function_tool: agents.tool.FunctionTool 对象

    Returns:
        OpenHands Tool 对象
    """
    # 提取 FunctionTool 的属性
    tool_name = function_tool.name
    tool_description = function_tool.description
    params_schema = function_tool.params_json_schema
    on_invoke = function_tool.on_invoke_tool

    # 创建执行器函数（直接使用原始函数）
    async def executor(params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            # 调用原始的 on_invoke_tool 函数
            # FunctionTool 的 on_invoke_tool 签名是: (params: dict) -> str
            if hasattr(on_invoke, '__call__'):
                # 检查是否是异步函数
                import inspect
                if inspect.iscoroutinefunction(on_invoke):
                    result = await on_invoke(params)
                else:
                    result = on_invoke(params)
            else:
                result = str(on_invoke)

            return {
                "result": result,
                "error": None
            }
        except Exception as e:
            return {
                "result": None,
                "error": str(e)
            }

    # 创建 OpenHands Tool
    # 注意：OpenHands 的 Tool 使用更简单的方式
    # 我们直接使用 ToolSpec + 注册函数的方式
    tool = ToolSpec(
        name=tool_name,
        params=params_schema
    )

    # 将执行器存储为工具的元数据
    # 这样在工具注册时可以使用
    if not hasattr(tool, '_executor'):
        tool._executor = executor
        tool._description = tool_description

    return tool


def register_function_tools(function_tools: list) -> list[ToolSpec]:
    """
    批量注册 FunctionTool 并返回 ToolSpec 列表

    这个函数会：
    1. 将每个 FunctionTool 转换为 ToolSpec
    2. 返回 ToolSpec 列表（用于传给 Agent）

    注意：由于 OpenHands SDK 的工具系统复杂性，我们采用简化方案：
    - Agent 接收 ToolSpec（工具声明）
    - 实际的工具执行由 Agent 内部通过 LLM 的 function calling 处理
    - 本地工具的执行逻辑需要在 Conversation 层面处理

    Args:
        function_tools: FunctionTool 对象列表

    Returns:
        ToolSpec 列表
    """
    toolspecs = []

    for function_tool in function_tools:
        # 创建 ToolSpec（只包含声明信息）
        toolspec = ToolSpec(
            name=function_tool.name,
            params=function_tool.params_json_schema
        )

        # 存储原始的 on_invoke_tool 以便后续使用
        # 这是一个临时方案，实际执行需要在 Conversation 层面处理
        toolspec._original_function_tool = function_tool

        toolspecs.append(toolspec)

    return toolspecs


def convert_function_tool_to_toolspec(function_tool) -> ToolSpec:
    """
    将 FunctionTool (OpenAI Agents SDK) 转换为 OpenHands ToolSpec

    ToolSpec 只包含工具的声明信息，不包含执行逻辑

    Args:
        function_tool: agents.tool.FunctionTool 对象

    Returns:
        OpenHands ToolSpec 对象
    """
    toolspec = ToolSpec(
        name=function_tool.name,
        params=function_tool.params_json_schema
    )

    # 保存原始 FunctionTool 的引用
    toolspec._original_function_tool = function_tool

    return toolspec
