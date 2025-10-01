# 工具转换问题解决方案

## 问题描述

```
ValidationError: 70 validation errors for Agent
tools.0
  Input should be a valid dictionary or instance of ToolSpec
  [type=model_type, input_value=FunctionTool(...), input_type=FunctionTool]
```

**原因**: OpenHands Agent 期望 `list[ToolSpec]`，但我们传入了 `FunctionTool` 对象（OpenAI Agents SDK 格式）。

## 解决方案

### 1. 创建工具适配器 (`utils/openhands_adapter/tool_adapter.py`)

提供三个核心函数：

#### `convert_function_tool_to_openhands(function_tool) -> Tool`
将 FunctionTool 转换为 OpenHands Tool 对象（包含执行逻辑）

**转换逻辑**:
```python
def convert_function_tool_to_openhands(function_tool) -> Tool:
    # 1. 提取 FunctionTool 属性
    tool_name = function_tool.name
    tool_description = function_tool.description
    params_schema = function_tool.params_json_schema
    on_invoke = function_tool.on_invoke_tool

    # 2. 创建自定义 Action 类
    class CustomAction(Action):
        tool_name: str = tool_name
        params: Dict[str, Any] = {}

    # 3. 创建自定义 Observation 类
    class CustomObservation(Observation):
        result: Any = None
        error: str | None = None

    # 4. 创建执行器
    async def executor(action: CustomAction) -> CustomObservation:
        result = await on_invoke(action.params)
        return CustomObservation(result=result)

    # 5. 返回 OpenHands Tool
    return Tool(
        name=tool_name,
        description=tool_description,
        action_type=CustomAction,
        observation_type=CustomObservation,
        executor=executor
    )
```

#### `register_function_tools(function_tools: list) -> list[ToolSpec]`
批量注册工具并返回 ToolSpec 列表

**处理流程**:
```python
def register_function_tools(function_tools: list) -> list[ToolSpec]:
    toolspecs = []
    for function_tool in function_tools:
        # 1. 转换为 OpenHands Tool
        tool = convert_function_tool_to_openhands(function_tool)

        # 2. 注册到工具注册表
        register_tool(tool.name, tool)

        # 3. 创建 ToolSpec（用于 Agent）
        toolspec = ToolSpec(
            name=tool.name,
            params=function_tool.params_json_schema
        )
        toolspecs.append(toolspec)

    return toolspecs
```

### 2. 更新 `setup_agent()` 方法

**之前（错误）**:
```python
# 2. 收集本地工具
local_tools = []  # FunctionTool 对象
...

# 4. 创建 Agent
self.agent = OpenHandsAgent(
    llm=self.llm,
    tools=local_tools,  # ❌ 传入 FunctionTool 对象
    ...
)
```

**之后（正确）**:
```python
# 2. 收集本地 FunctionTool 对象
local_function_tools = []
for tool_name in self.task_config.needed_local_tools:
    tool_or_toolsets = local_tool_mappings[tool_name]
    if isinstance(tool_or_toolsets, list):
        local_function_tools.extend(tool_or_toolsets)
    else:
        local_function_tools.append(tool_or_toolsets)

# 3. 转换为 OpenHands ToolSpec
local_toolspecs = register_function_tools(local_function_tools)

# 4. 合并 MCP tools
mcp_toolspecs = []
if hasattr(self, 'mcp_tools') and self.mcp_tools:
    for mcp_tool in self.mcp_tools:
        if hasattr(mcp_tool, 'to_toolspec'):
            mcp_toolspecs.append(mcp_tool.to_toolspec())
        else:
            # 兜底逻辑
            mcp_toolspecs.append(ToolSpec(
                name=mcp_tool.name,
                params=mcp_tool.annotations.params if hasattr(mcp_tool, 'annotations') else {}
            ))

all_toolspecs = local_toolspecs + mcp_toolspecs

# 5. 创建 Agent
self.agent = OpenHandsAgent(
    llm=self.llm,
    tools=all_toolspecs,  # ✅ 传入 ToolSpec 列表
    ...
)
```

## 架构说明

### OpenHands 工具系统

```
┌─────────────────┐
│  FunctionTool   │ (OpenAI Agents SDK)
│  - name         │
│  - description  │
│  - params       │
│  - on_invoke    │
└────────┬────────┘
         │
         │ convert_function_tool_to_openhands()
         ▼
┌─────────────────┐
│      Tool       │ (OpenHands SDK - 完整工具)
│  - name         │
│  - description  │
│  - action_type  │
│  - executor     │────┐
└────────┬────────┘    │
         │             │ register_tool()
         │             ▼
         │     ┌────────────────┐
         │     │ Tool Registry  │ (全局注册表)
         │     └────────────────┘
         │
         │ to ToolSpec
         ▼
┌─────────────────┐
│    ToolSpec     │ (OpenHands SDK - 工具声明)
│  - name         │
│  - params       │
└────────┬────────┘
         │
         │ 传给 Agent
         ▼
┌─────────────────┐
│      Agent      │
│  - llm          │
│  - tools        │ ← list[ToolSpec]
└─────────────────┘
```

### 工具调用流程

1. **Agent 决策**: Agent 根据 ToolSpec 决定调用哪个工具
2. **查找工具**: 从工具注册表找到对应的 Tool 对象
3. **执行工具**: 调用 Tool 的 executor 函数
4. **返回结果**: Observation 返回给 Agent

## 关键差异

| 方面 | OpenAI Agents SDK | OpenHands SDK |
|------|-------------------|---------------|
| 工具格式 | `FunctionTool` | `Tool` (完整) + `ToolSpec` (声明) |
| 工具列表 | 直接传 FunctionTool | 传 ToolSpec 列表 |
| 工具注册 | 无需注册 | 需要注册到全局注册表 |
| 执行逻辑 | `on_invoke_tool` 函数 | `executor` async 函数 |
| 参数传递 | 字典 | Action 对象 |
| 结果返回 | 字符串 | Observation 对象 |

## 兼容性处理

### User Simulator 工具列表

User simulator 仍需要 OpenAI 格式的工具定义：

```python
# 从 FunctionTool 提取
for function_tool in local_function_tools:
    self.all_tools.append({
        "type": "function",
        "function": {
            "name": function_tool.name,
            "description": function_tool.description,
            "parameters": function_tool.params_json_schema
        }
    })

# 从 MCP Tool 提取
for mcp_tool in self.mcp_tools:
    if hasattr(mcp_tool, 'to_openai_tool'):
        openai_tool = mcp_tool.to_openai_tool()
        self.all_tools.append(openai_tool)
```

## 测试验证

```bash
uv run python -c "
from utils.aux_tools.basic import tool_sleep
from utils.openhands_adapter import register_function_tools

# 转换工具
toolspecs = register_function_tools([tool_sleep])

print('✓ Tool converted successfully')
print(f'  ToolSpec: {toolspecs[0].name}')
print(f'  Params: {toolspecs[0].params}')
"
```

## 修改文件

1. ✅ `utils/openhands_adapter/tool_adapter.py` - 新建
2. ✅ `utils/openhands_adapter/__init__.py` - 更新导出
3. ✅ `utils/roles/task_agent.py` - 更新 setup_agent()

## 注意事项

1. **异步执行**: OpenHands 的 executor 必须是 async 函数
2. **工具注册**: 必须在创建 Agent 之前注册工具
3. **全局注册表**: 工具注册是全局的，需要避免名称冲突
4. **MCP 工具**: MCP 工具已经是 OpenHands 格式，只需提取 ToolSpec

## 下一步

修复完成后，Agent 应该能够正确接受工具列表并进行初始化。
