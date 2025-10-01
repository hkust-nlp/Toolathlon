# 工具执行问题解决方案（最终版）

## 问题历程

### 问题1: 闭包作用域错误
```
NameError: name 'tool_name' is not defined
```

**原因**: 在类定义内部使用闭包变量，Python 类定义作用域不能直接访问外层函数变量

### 解决方案：简化工具转换

意识到 OpenHands 的工具系统设计：
- **ToolSpec**: 工具声明（name + params schema）
- **Tool**: 完整工具对象（包含执行逻辑）
- **Agent**: 只需要 ToolSpec 列表

## 最终实现

### 1. 简化的工具适配器 (`utils/openhands_adapter/tool_adapter.py`)

```python
def register_function_tools(function_tools: list) -> list[ToolSpec]:
    """
    批量转换 FunctionTool 为 ToolSpec

    策略：
    - 只创建 ToolSpec（工具声明）
    - 保存原始 FunctionTool 引用
    - 实际执行在 task_agent 层面处理
    """
    toolspecs = []

    for function_tool in function_tools:
        # 创建 ToolSpec
        toolspec = ToolSpec(
            name=function_tool.name,
            params=function_tool.params_json_schema
        )

        # 保存原始引用（用于后续执行）
        toolspec._original_function_tool = function_tool

        toolspecs.append(toolspec)

    return toolspecs
```

### 2. 工具执行器映射 (`task_agent.py`)

**在 `__init__` 中添加**:
```python
self.local_tool_executors: Dict[str, Callable] = {}
```

**在 `setup_agent()` 中保存执行器**:
```python
# 保存本地工具的执行器映射
for function_tool in local_function_tools:
    self.local_tool_executors[function_tool.name] = function_tool.on_invoke_tool
```

### 3. 事件回调中执行本地工具 (`_on_event()`)

```python
elif isinstance(event, ActionEvent):
    # 工具调用
    self.stats["cumulative_tool_calls"] += 1

    # 检查是否是本地工具
    if event.tool_name in self.local_tool_executors:
        try:
            executor = self.local_tool_executors[event.tool_name]

            # 从 tool_call 中提取参数
            if hasattr(event, 'tool_call') and event.tool_call:
                if hasattr(event.tool_call.function, 'arguments'):
                    args_str = event.tool_call.function.arguments
                    params = json.loads(args_str)

            # 执行工具
            if inspect.iscoroutinefunction(executor):
                # 异步执行器 - 由 conversation 处理
                pass
            else:
                # 同步执行器 - 可以立即执行
                result = executor(params)
        except Exception as e:
            print(f"Local tool error: {e}")
```

## OpenHands 工具执行机制

### MCP 工具
- ✅ OpenHands 内置支持
- ✅ 通过 `create_mcp_tools()` 创建
- ✅ 自动执行（连接 MCP 服务器）

### 本地工具
- ⚠️ 需要手动处理
- 策略1: 在 `_on_event` 中拦截并执行（当前实现）
- 策略2: 将本地工具包装为 MCP 服务器
- 策略3: 使用 OpenHands 的 Tool 注册机制（复杂）

## 当前实现的局限性

### 1. 同步 vs 异步
- ✅ 同步工具可以在 `_on_event` 中执行
- ⚠️ 异步工具需要在异步上下文中执行
- 解决方案：OpenHands 内部应该会处理

### 2. 工具结果返回
- ❓ 在 `_on_event` 中执行的工具结果如何返回给 Agent？
- 可能需要：
  - 创建 ObservationEvent
  - 添加到 conversation.state.events
  - 但这需要访问 conversation 的内部状态

### 3. 替代方案：依赖 OpenHands 内部机制

实际上，OpenHands 可能已经有机制处理这个问题：
1. Agent 通过 LLM 决定调用工具
2. LLM 返回 function call
3. OpenHands 查找工具注册表
4. 如果工具已注册，执行并返回结果

**我们可能不需要在 `_on_event` 中手动执行！**

## 测试建议

1. **基本测试**：检查 Agent 是否能正确创建
2. **工具调用测试**：让 Agent 调用一个简单的本地工具
3. **观察日志**：查看 ActionEvent 和 ObservationEvent

## 修改文件汇总

1. ✅ `utils/openhands_adapter/tool_adapter.py` - 简化实现
2. ✅ `utils/roles/task_agent.py`:
   - 添加 `local_tool_executors` 字典
   - 在 `setup_agent()` 中保存执行器
   - 在 `_on_event()` 中添加本地工具执行逻辑（调试用）

## 注意事项

1. **当前实现是过渡方案**：
   - 本地工具通过 ToolSpec 声明给 Agent
   - 执行逻辑保存在 `local_tool_executors`
   - 实际执行可能由 OpenHands 内部处理

2. **MCP 工具优先**：
   - MCP 工具有完整的 OpenHands 支持
   - 如果可能，将本地工具迁移为 MCP 服务器

3. **验证需求**：
   - 运行实际测试确认工具调用是否工作
   - 检查 ObservationEvent 是否包含正确的结果

## 下一步

1. 测试基本功能
2. 观察工具调用流程
3. 根据实际行为调整实现
