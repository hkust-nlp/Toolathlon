"""
OpenHands Tool Adapter

将 OpenAI Agents SDK 的 FunctionTool 转换为 OpenHands SDK 的 Tool 格式
"""

from typing import Any, Dict, Callable
from openhands.sdk.tool import Tool, ToolSpec, ToolExecutor, register_tool
from openhands.sdk.tool.schema import Action, Observation
import inspect


def create_action_class(tool_name: str):
    """动态创建 Action 类"""
    class CustomAction(Action):
        """Custom action for tool"""
        pass

    # 设置类名
    CustomAction.__name__ = f"{tool_name}Action"
    CustomAction.__qualname__ = f"{tool_name}Action"

    return CustomAction


def create_observation_class(tool_name: str):
    """动态创建 Observation 类"""
    class CustomObservation(Observation):
        """Custom observation for tool"""
        content: str = ""
        error: str | None = None

    # 设置类名
    CustomObservation.__name__ = f"{tool_name}Observation"
    CustomObservation.__qualname__ = f"{tool_name}Observation"

    return CustomObservation


def create_executor_class(tool_name: str, on_invoke: Callable, ObservationClass):
    """动态创建 ToolExecutor 类"""
    class CustomExecutor(ToolExecutor):
        """Custom executor for tool"""

        def __call__(self, action: Action) -> Observation:
            """执行工具调用"""
            try:
                # 从 action 中提取参数
                # Action 对象的属性就是参数
                params = {}
                if hasattr(action, '__dict__'):
                    for key, value in action.__dict__.items():
                        if not key.startswith('_') and key not in ['kind', 'thought', 'tool_name']:
                            params[key] = value

                # 调用原始的 on_invoke_tool 函数
                if inspect.iscoroutinefunction(on_invoke):
                    # 如果是异步函数，需要在异步上下文中执行
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 如果事件循环正在运行，创建一个 task
                            result = asyncio.create_task(on_invoke(params))
                        else:
                            result = loop.run_until_complete(on_invoke(params))
                    except RuntimeError:
                        # 没有事件循环，创建一个新的
                        result = asyncio.run(on_invoke(params))
                else:
                    result = on_invoke(params)

                # 返回 Observation
                return ObservationClass(
                    content=str(result),
                    error=None
                )
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                return ObservationClass(
                    content="",
                    error=error_msg
                )

    # 设置类名
    CustomExecutor.__name__ = f"{tool_name}Executor"
    CustomExecutor.__qualname__ = f"{tool_name}Executor"

    return CustomExecutor


def convert_function_tool_to_openhands(function_tool):
    """
    将 FunctionTool (OpenAI Agents SDK) 转换为 OpenHands Tool 类

    Args:
        function_tool: agents.tool.FunctionTool 对象

    Returns:
        (tool_class, tool_name) 元组
    """
    # 提取 FunctionTool 的属性
    tool_name = function_tool.name
    tool_description = function_tool.description
    params_schema = function_tool.params_json_schema
    on_invoke = function_tool.on_invoke_tool

    # 动态创建 Action 和 Observation 类
    ActionClass = create_action_class(tool_name)
    ObservationClass = create_observation_class(tool_name)

    # 动态创建 Executor 类
    ExecutorClass = create_executor_class(tool_name, on_invoke, ObservationClass)

    # 创建 Tool 子类（而不是实例）
    class CustomTool(Tool):
        """Custom tool class"""

        @classmethod
        def create(cls, conv_state=None, **params):
            """创建工具实例的工厂方法"""
            # 返回 Sequence[Tool]（列表）
            return [cls(
                name=tool_name,
                description=tool_description,
                action_type=ActionClass,
                observation_type=ObservationClass,
                executor=ExecutorClass()
            )]

    # 设置类名
    CustomTool.__name__ = f"{tool_name}Tool"
    CustomTool.__qualname__ = f"{tool_name}Tool"

    return CustomTool, tool_name


def register_function_tools(function_tools: list) -> list[ToolSpec]:
    """
    批量注册 FunctionTool 并返回 ToolSpec 列表

    这个函数会：
    1. 将每个 FunctionTool 转换为 OpenHands Tool 类
    2. 注册到 OpenHands 工具注册表
    3. 返回 ToolSpec 列表（用于传给 Agent）

    Args:
        function_tools: FunctionTool 对象列表

    Returns:
        ToolSpec 列表
    """
    toolspecs = []

    for function_tool in function_tools:
        # 转换为 OpenHands Tool 类（而不是实例）
        tool_class, tool_name = convert_function_tool_to_openhands(function_tool)

        # 注册工具类到 OpenHands 注册表
        register_tool(tool_name, tool_class)

        # 创建 ToolSpec（传递参数 schema）
        toolspec = ToolSpec(
            name=tool_name,
            params=function_tool.params_json_schema
        )

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

    return toolspec
