"""
OpenHands Tool Adapter

将 OpenAI Agents SDK 的 FunctionTool 转换为 OpenHands SDK 的 Tool 格式
"""

from typing import Any, Dict, Callable
from openhands.sdk.tool import Tool, ToolSpec, ToolExecutor, register_tool
from openhands.sdk.tool.schema import Action, Observation
import inspect


def create_action_class(tool_name: str, params_schema: dict):
    """动态创建 Action 类，根据参数 schema 添加字段"""
    from pydantic import Field, field_validator, create_model
    from typing import Any

    # 动态创建类名
    action_class_name = f"{tool_name}Action"

    # 从 params_schema 提取字段定义
    properties = params_schema.get('properties', {})
    required_fields = params_schema.get('required', [])

    # 构建 Pydantic 字段字典
    fields = {}
    for field_name, field_info in properties.items():
        field_type = Any  # 默认类型
        field_default = ...  # 默认为必需

        # 根据 JSON schema 类型确定 Python 类型
        json_type = field_info.get('type', 'string')
        if json_type == 'string':
            field_type = str
        elif json_type == 'integer':
            field_type = int
        elif json_type == 'number':
            field_type = float
        elif json_type == 'boolean':
            field_type = bool
        elif json_type == 'array':
            field_type = list
        elif json_type == 'object':
            field_type = dict

        # 确定默认值
        if field_name not in required_fields:
            if 'default' in field_info:
                field_default = field_info['default']
            else:
                field_default = None
                field_type = field_type | None  # 可选字段

        # 创建 Field
        description = field_info.get('description', '')
        fields[field_name] = (field_type, Field(default=field_default, description=description))

    # 使用 create_model 动态创建模型，继承自 Action
    CustomAction = create_model(
        action_class_name,
        __base__=Action,
        **fields
    )

    # 添加 field_validator 来强制 kind 字段值
    def force_kind_value(v):
        """强制 kind 字段始终是类名，忽略外部输入"""
        return action_class_name

    # 使用 __pydantic_decorators__ 添加 validator（如果可能）
    # 或者覆盖 __init__ 方法
    original_init = CustomAction.__init__

    def custom_init(self, **data):
        # 强制设置 kind 字段
        data['kind'] = action_class_name
        original_init(self, **data)

    CustomAction.__init__ = custom_init

    # 覆盖 model_json_schema 方法，移除 kind 字段
    original_model_json_schema = CustomAction.model_json_schema

    @classmethod
    def custom_model_json_schema(cls, **kwargs):
        """覆盖 JSON schema 生成，移除 kind 字段"""
        schema = original_model_json_schema(**kwargs)
        # 从 properties 中删除 kind
        if 'properties' in schema and 'kind' in schema['properties']:
            del schema['properties']['kind']
        # 从 required 中删除 kind（如果存在）
        if 'required' in schema and 'kind' in schema['required']:
            schema['required'].remove('kind')
        return schema

    CustomAction.model_json_schema = custom_model_json_schema

    # 设置 kind 字段的默认值
    if 'kind' in CustomAction.model_fields:
        CustomAction.model_fields['kind'].default = action_class_name

    return CustomAction


def create_observation_class(tool_name: str):
    """动态创建 Observation 类"""
    from pydantic import Field
    from openhands.sdk.llm import TextContent

    # 使用 tool_name 构建类名
    observation_class_name = f"{tool_name}Observation"

    # 定义 to_llm_content 方法实现
    def to_llm_content_impl(self):
        """返回 LLM 格式的内容"""
        if self.error:
            return [TextContent(text=f"Error: {self.error}")]
        return [TextContent(text=self.content)]

    # 使用 type() 一步创建类
    # 关键：直接使用正确的类名，不创建中间模板
    CustomObservation = type(
        observation_class_name,  # ✅ 正确的、唯一的类名
        (Observation,),          # 基类
        {
            '__module__': __name__,
            '__annotations__': {
                'content': str,
                'error': str | None,
            },
            'content': Field(default=""),
            'error': Field(default=None),
            'to_llm_content': property(to_llm_content_impl),  # ✅ 添加 property
        }
    )

    # 设置 kind 字段的默认值
    if 'kind' in CustomObservation.model_fields:
        CustomObservation.model_fields['kind'].default = observation_class_name

    # 重建模型以应用更改
    CustomObservation.model_rebuild()

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
                        if not key.startswith('_') and key not in ['kind']:
                            params[key] = value

                # 从 Pydantic 模型中提取字段
                if hasattr(action, 'model_dump'):
                    params = action.model_dump(exclude={'kind'})

                # 检查 on_invoke 的签名
                import json
                sig = inspect.signature(on_invoke)
                param_names = list(sig.parameters.keys())

                # 调用原始的 on_invoke_tool 函数
                if inspect.iscoroutinefunction(on_invoke):
                    import asyncio
                    import concurrent.futures
                    import threading

                    # 异步函数 - 在新线程的新事件循环中运行
                    def run_async_in_thread(coro):
                        """在新线程中运行异步函数，避免事件循环冲突"""
                        def thread_func():
                            # 创建新的事件循环
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return loop.run_until_complete(coro)
                            finally:
                                loop.close()

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(thread_func)
                            return future.result()

                    if len(param_names) == 2:
                        # 期望 (context, params_str) - 旧的 OpenAI Agents SDK 格式
                        params_str = json.dumps(params)
                        result = run_async_in_thread(on_invoke(None, params_str))
                    else:
                        # 期望 (params) - 新格式
                        result = run_async_in_thread(on_invoke(params))
                else:
                    # 同步函数
                    if len(param_names) == 2:
                        # 期望 (context, params_str)
                        params_str = json.dumps(params)
                        result = on_invoke(None, params_str)
                    else:
                        # 期望 (params)
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

    # 动态创建 Action 和 Observation 类，传递参数 schema
    ActionClass = create_action_class(tool_name, params_schema)
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
