# OpenHands SDK 替换 - 错误修复总结

## 修复的所有错误

### ❌ 错误 1: max_tokens 参数不支持

**报错**:
```
ValidationError: 1 validation error for LLM
max_tokens
  Extra inputs are not permitted [type=extra_forbidden, input_value=4096]
```

**原因**: OpenHands LLM 使用 `max_output_tokens` 而不是 `max_tokens`

**修复**:
- 文件: `utils/openhands_adapter/llm_adapter.py`
- 将 `"max_tokens": max_tokens` 改为 `"max_output_tokens": max_tokens`

**文档**: `PARAMETER_MAPPING.md`

---

### ❌ 错误 2: 工具类型不匹配

**报错**:
```
ValidationError: 70 validation errors for Agent
tools.0
  Input should be a valid dictionary or instance of ToolSpec
  [input_value=FunctionTool(...), input_type=FunctionTool]
```

**原因**: Agent 期望 `list[ToolSpec]`，我们传入了 `FunctionTool` 对象

**修复**:
- 文件: `utils/openhands_adapter/tool_adapter.py` (新建)
- 创建 `register_function_tools()` 函数将 FunctionTool 转换为 ToolSpec
- 在 `task_agent.py` 中使用转换后的 ToolSpec 列表

**文档**: `TOOL_CONVERSION_FIX.md`

---

### ❌ 错误 3: 闭包作用域问题

**报错**:
```
NameError: name 'tool_name' is not defined
  File "tool_adapter.py", line 31, in CustomAction
    tool_name: str = tool_name
```

**原因**: 类定义作用域不能直接访问外层函数的变量

**修复**:
- 简化 `tool_adapter.py` 实现
- 只创建 ToolSpec（不创建完整的 Tool 对象）
- 在 `task_agent.py` 中保存工具执行器映射

**文档**: `TOOL_EXECUTION_FINAL.md`

---

### ❌ 错误 4: Conversation 参数名称错误

**报错**:
```
TypeError: Conversation.__new__() got an unexpected keyword argument 'working_dir'
```

**原因**: Conversation 使用 `workspace` 参数，不是 `working_dir`

**修复**:
- 文件: `utils/roles/task_agent.py`
- 将 `working_dir=` 改为 `workspace=`

**文档**: `CONVERSATION_PARAMETER_FIX.md`

---

## 参数映射总表

| 原框架/预期 | OpenHands 实际 | 位置 | 状态 |
|------------|---------------|------|------|
| `max_tokens` | `max_output_tokens` | LLM | ✅ 已修复 |
| `FunctionTool` | `ToolSpec` | Agent.tools | ✅ 已修复 |
| `working_dir` | `workspace` | Conversation | ✅ 已修复 |

## 修改的文件列表

### 新建文件
1. ✅ `utils/openhands_adapter/tool_adapter.py` - 工具转换器
2. ✅ `PARAMETER_MAPPING.md` - 参数映射文档
3. ✅ `TOOL_CONVERSION_FIX.md` - 工具转换文档
4. ✅ `TOOL_EXECUTION_FINAL.md` - 工具执行文档
5. ✅ `CONVERSATION_PARAMETER_FIX.md` - Conversation 参数文档

### 修改文件
1. ✅ `utils/openhands_adapter/__init__.py` - 添加工具转换导出
2. ✅ `utils/openhands_adapter/llm_adapter.py` - 修复 max_tokens
3. ✅ `utils/roles/task_agent.py` - 完整替换 agent loop

## 关键代码片段

### LLM 创建
```python
llm = LLM(
    model="claude-sonnet-4-20250514",
    temperature=0.6,
    max_output_tokens=4096,  # ✅ 正确参数
    top_p=1.0,
)
```

### 工具转换
```python
# 转换 FunctionTool 为 ToolSpec
local_toolspecs = register_function_tools(local_function_tools)

# 保存执行器映射
for function_tool in local_function_tools:
    self.local_tool_executors[function_tool.name] = function_tool.on_invoke_tool
```

### Agent 创建
```python
agent = OpenHandsAgent(
    llm=self.llm,
    tools=local_toolspecs,  # ✅ ToolSpec 列表
    system_message=system_prompt,
)
```

### Conversation 创建
```python
conversation = Conversation(
    agent=self.agent,
    workspace=str(workspace_path),  # ✅ 正确参数名
    persistence_dir=str(persistence_dir),
    max_iteration_per_run=max_inner_turns,
    callbacks=[self._on_event],
    visualize=False,
)
```

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     TaskAgent                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────┐     │
│  │         LLM (OpenHands)                      │     │
│  │  - model: claude-sonnet-4                    │     │
│  │  - max_output_tokens: 4096 ✅                │     │
│  └──────────────────────────────────────────────┘     │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────┐     │
│  │         Agent (OpenHands)                    │     │
│  │  - llm: LLM                                  │     │
│  │  - tools: list[ToolSpec] ✅                  │     │
│  │  - system_message: str                       │     │
│  └──────────────────────────────────────────────┘     │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────┐     │
│  │     Conversation (OpenHands)                 │     │
│  │  - agent: Agent                              │     │
│  │  - workspace: str ✅                         │     │
│  │  - callbacks: [_on_event]                    │     │
│  └──────────────────────────────────────────────┘     │
│                                                         │
│  ┌──────────────────────────────────────────────┐     │
│  │     Tool Execution                           │     │
│  │  - local_tool_executors: Dict[str, Callable]│     │
│  │  - _on_event: 拦截并执行本地工具             │     │
│  └──────────────────────────────────────────────┘     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 测试建议

### 1. 基本初始化测试
```bash
uv run demo.py \
  --eval_config scripts/temp_and_debug/debug_eval_config.json \
  --task_dir debug/debug-task \
  --debug
```

**预期**: Agent 和 Conversation 成功创建，无报错

### 2. 工具调用测试
选择一个使用本地工具的任务，观察：
- ActionEvent 是否正确触发
- 工具参数是否正确提取
- ObservationEvent 是否包含结果

### 3. MCP 工具测试
选择一个使用 MCP 服务器的任务，验证：
- MCP 工具是否正确加载
- 工具调用是否成功
- 结果是否正确返回

## 潜在问题

### 1. 本地工具执行
- ⚠️ 当前在 `_on_event` 中执行（监控模式）
- ✅ OpenHands 应该会通过 LLM function calling 自动处理
- 📝 需要实际测试确认

### 2. 异步工具
- ⚠️ 异步工具需要在异步上下文中执行
- ✅ OpenHands Conversation 内部应该处理

### 3. 工具结果返回
- ⚠️ 需要确认 ObservationEvent 是否正确生成
- ✅ OpenHands 内部应该自动处理

## 成功标志

当看到以下输出时，表示所有修复都成功了：

```
Created OpenHands LLM: claude-sonnet-4-20250514
Registered 3 local tools
  - local-sleep
  - local-claim_done
  - local-manage_context
Agent will use 3 local tools + 12 MCP tools
Created OpenHands Conversation: <uuid>
Populated 15 tools for User simulator compatibility
=== Starting interaction loop (OpenHands) ===
```

## 下一步

1. ✅ 所有错误已修复
2. ⏳ 运行基本功能测试
3. ⏳ 验证工具调用流程
4. ⏳ 根据实际行为微调

---

**修复完成时间**: 2025-10-02
**总计修复错误**: 4 个
**修改文件数**: 3 个核心文件 + 5 个文档文件
**状态**: ✅ 准备测试
