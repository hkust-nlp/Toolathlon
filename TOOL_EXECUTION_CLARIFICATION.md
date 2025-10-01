# 工具执行流程详解：本地工具 vs MCP 工具

## 两种工具的完整流程

### 1. 本地工具 (Local Tools)

```
┌─────────────────────────────────────────────────────────┐
│          本地工具执行流程                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  定义阶段:                                               │
│  ┌──────────────────────────────────────────┐         │
│  │ FunctionTool (OpenAI Agents SDK)         │         │
│  │ - name: "local-sleep"                    │         │
│  │ - params_json_schema: {...}              │         │
│  │ - on_invoke_tool: callable               │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  转换阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ register_function_tools()                │         │
│  │ → 创建 ToolSpec                          │         │
│  │ → 保存到 local_tool_executors           │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  注册阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ Agent.tools ← ToolSpec                   │         │
│  │ task_agent.local_tool_executors ←        │         │
│  │   {                                      │         │
│  │     "local-sleep": on_sleep_invoke,      │         │
│  │     "local-claim_done": on_done_invoke   │         │
│  │   }                                      │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  执行阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ LLM 决定调用工具                          │         │
│  │   → ActionEvent 触发                     │         │
│  │   → _on_event() 拦截                     │         │
│  │   → 检查 local_tool_executors            │         │
│  │   → 提取参数并执行 on_invoke_tool        │         │
│  │   → (OpenHands 内部也可能执行)           │         │
│  │   → ObservationEvent 返回结果            │         │
│  └──────────────────────────────────────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2. MCP 工具 (MCP Tools)

```
┌─────────────────────────────────────────────────────────┐
│          MCP 工具执行流程                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  定义阶段:                                               │
│  ┌──────────────────────────────────────────┐         │
│  │ YAML 配置文件                            │         │
│  │ configs/mcp_servers/filesystem.yaml      │         │
│  │ - command: npx                           │         │
│  │ - args: [@modelcontextprotocol/...]     │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  转换阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ create_openhands_mcp_config()            │         │
│  │ → 转换 YAML 为 OpenHands Dict 格式       │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  创建阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ openhands_create_mcp_tools()             │         │
│  │ → 连接 MCP 服务器                        │         │
│  │ → 获取工具列表                           │         │
│  │ → 创建 MCPTool 对象                      │         │
│  │   - 包含完整的执行逻辑                   │         │
│  │   - 内置 MCP 协议通信                    │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  注册阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ 从 MCPTool 提取 ToolSpec                 │         │
│  │   → Agent.tools ← ToolSpec               │         │
│  │                                          │         │
│  │ MCPTool 本身已注册到 OpenHands           │         │
│  │ (不需要 local_tool_executors)            │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                   │
│  执行阶段:           ↓                                   │
│  ┌──────────────────────────────────────────┐         │
│  │ LLM 决定调用工具                          │         │
│  │   → ActionEvent 触发                     │         │
│  │   → OpenHands 内部处理                   │         │
│  │   → 查找 MCPTool                         │         │
│  │   → MCPTool 自动连接 MCP 服务器          │         │
│  │   → 执行工具并获取结果                   │         │
│  │   → 断开连接                             │         │
│  │   → ObservationEvent 返回结果            │         │
│  └──────────────────────────────────────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 关键差异对比

| 方面 | 本地工具 (Local Tools) | MCP 工具 (MCP Tools) |
|------|----------------------|---------------------|
| **定义来源** | Python 代码 (FunctionTool) | YAML 配置 + MCP 服务器 |
| **转换函数** | `register_function_tools()` | `openhands_create_mcp_tools()` |
| **工具类型** | ToolSpec (声明) | MCPTool (完整对象) |
| **执行器存储** | `local_tool_executors` 字典 | MCPTool 对象内部 |
| **执行方式** | `_on_event()` 拦截 (临时) | OpenHands 内部自动处理 ✅ |
| **连接管理** | 无需连接 | 自动连接/断开 MCP 服务器 |
| **OpenHands 支持** | 需要手动处理 ⚠️ | 原生支持 ✅ |

## 在 task_agent.py 中的实现

### setup_agent() 方法

```python
async def setup_agent(self) -> None:
    # 1. 处理本地工具
    local_function_tools = []  # FunctionTool 对象
    for tool_name in self.task_config.needed_local_tools:
        tool_or_toolsets = local_tool_mappings[tool_name]
        local_function_tools.extend(...)

    # 转换为 ToolSpec
    local_toolspecs = register_function_tools(local_function_tools)

    # 保存执行器（仅本地工具）
    for function_tool in local_function_tools:
        self.local_tool_executors[function_tool.name] = function_tool.on_invoke_tool

    # 2. 处理 MCP 工具
    # MCP 工具已经在 setup_mcp_servers() 中创建为 MCPTool
    mcp_toolspecs = []
    if hasattr(self, 'mcp_tools') and self.mcp_tools:
        for mcp_tool in self.mcp_tools:  # MCPTool 对象
            # 提取 ToolSpec
            if hasattr(mcp_tool, 'to_toolspec'):
                mcp_toolspecs.append(mcp_tool.to_toolspec())

    # 3. 合并所有 ToolSpec
    all_toolspecs = local_toolspecs + mcp_toolspecs

    # 4. 创建 Agent
    self.agent = OpenHandsAgent(
        llm=self.llm,
        tools=all_toolspecs,  # 包含本地 + MCP
        ...
    )
```

### _on_event() 回调

```python
def _on_event(self, event) -> None:
    if isinstance(event, ActionEvent):
        # 统计所有工具调用
        self.stats["cumulative_tool_calls"] += 1

        # 仅处理本地工具
        if event.tool_name in self.local_tool_executors:
            # 本地工具：手动执行
            executor = self.local_tool_executors[event.tool_name]
            result = executor(params)

        # MCP 工具：OpenHands 自动处理，无需干预
```

## 工具调用流程示例

### 本地工具调用：`local-sleep`

```
1. LLM Response:
   {
     "tool_calls": [{
       "name": "local-sleep",
       "arguments": {"seconds": 5}
     }]
   }

2. OpenHands 创建 ActionEvent:
   ActionEvent(
     tool_name="local-sleep",
     tool_call={...},
     action=Action(...)
   )

3. _on_event() 拦截:
   - 检查: "local-sleep" in local_tool_executors ✅
   - 提取参数: {"seconds": 5}
   - 执行: on_sleep_tool_invoke({"seconds": 5})
   - 返回: "Slept for 5 seconds"

4. OpenHands 创建 ObservationEvent:
   ObservationEvent(
     tool_name="local-sleep",
     result="Slept for 5 seconds"
   )
```

### MCP 工具调用：`read_file`

```
1. LLM Response:
   {
     "tool_calls": [{
       "name": "read_file",
       "arguments": {"path": "/workspace/file.txt"}
     }]
   }

2. OpenHands 创建 ActionEvent:
   ActionEvent(
     tool_name="read_file",
     tool_call={...},
     action=Action(...)
   )

3. _on_event() 拦截:
   - 检查: "read_file" in local_tool_executors ✗
   - 跳过（不是本地工具）

4. OpenHands 内部处理:
   - 查找 MCPTool("read_file")
   - 连接 filesystem MCP 服务器
   - 发送 MCP 请求: read_file("/workspace/file.txt")
   - 接收 MCP 响应: "file content..."
   - 断开连接

5. OpenHands 创建 ObservationEvent:
   ObservationEvent(
     tool_name="read_file",
     result="file content..."
   )
```

## 为什么这样设计？

### 本地工具需要手动处理

1. **OpenHands 无法自动执行**: FunctionTool 只是一个数据结构，OpenHands 不知道如何执行
2. **我们只提供了 ToolSpec**: 只有工具的声明，没有执行逻辑
3. **临时解决方案**: 在 `_on_event()` 中手动拦截并执行

### MCP 工具自动处理

1. **OpenHands 原生支持**: MCPTool 是 OpenHands 的一等公民
2. **完整的执行逻辑**: MCPTool 内部包含 MCP 协议通信
3. **自动生命周期管理**: 自动连接/断开 MCP 服务器

## 潜在改进

### 方案 1: 将本地工具转为真正的 OpenHands Tool

```python
# 创建完整的 Tool 对象（而不只是 ToolSpec）
from openhands.sdk.tool import Tool

def create_openhands_tool(function_tool):
    async def executor(**kwargs):
        return function_tool.on_invoke_tool(kwargs)

    tool = Tool(
        name=function_tool.name,
        description=function_tool.description,
        executor=executor,
        ...
    )

    register_tool(tool.name, tool)
    return tool
```

### 方案 2: 将本地工具包装为 MCP 服务器

```python
# 创建一个本地 MCP 服务器
# 将所有本地工具作为 MCP 工具暴露
# 这样 OpenHands 就能统一处理
```

## 总结

**我上文的流程图仅适用于本地工具！**

完整的工具生态系统：

```
Agent.tools = [
    # 本地工具的 ToolSpec
    ToolSpec(name="local-sleep", ...),        ← 需要手动执行
    ToolSpec(name="local-claim_done", ...),   ← 需要手动执行

    # MCP 工具的 ToolSpec
    ToolSpec(name="read_file", ...),          ← OpenHands 自动执行
    ToolSpec(name="write_file", ...),         ← OpenHands 自动执行
    ToolSpec(name="search_files", ...),       ← OpenHands 自动执行
]

task_agent.local_tool_executors = {
    "local-sleep": on_sleep_invoke,           ← 仅本地工具
    "local-claim_done": on_done_invoke,       ← 仅本地工具
}

# MCP 工具不在 local_tool_executors 中
# 它们由 OpenHands 内部的 MCPTool 对象处理
```

希望这样更清楚了！🎯

  1. 导入 ToolExecutor：从 openhands.sdk.tool 导入 ToolExecutor 基类
  2. 创建 ToolExecutor 子类：新增 create_executor_class() 函数，动态创建继承自 ToolExecutor 的执行器类
  3. 实现 __call__ 方法：ToolExecutor 子类必须实现 __call__(self, action: Action) -> Observation 方法
  4. 处理异步函数：在 executor 中处理同步和异步的 on_invoke_tool 函数调用
  5. 传入实例：在创建 Tool 时，传入 ExecutorClass() 实例而不是函数