# mcpbench_dev - OpenHands Builtin Tools 使用分析

## 问题概述

当前 mcpbench_dev 的任务结束逻辑存在问题，导致：
1. Agent 无法正确结束任务
2. 达到 max_turns 后被强制停止
3. 即使任务完成也无法被识别

## OpenHands SDK Builtin Tools 的设计

### 1. Finish Tool 的作用

**文件**: `openhands/sdk/tool/builtins/finish.py`

```python
class FinishTool(Tool[FinishAction, ObservationBase]):
    name: str = "finish"

    def executor(self, action: FinishAction) -> ObservationBase:
        return ObservationBase(
            message=action.message,
            extra={"success": True}
        )
```

**设计意图**:
- Agent 主动调用 `finish` 工具来**明确标记任务完成**
- 不依赖外部停止条件或 max turns
- 提供清晰的任务完成语义

### 2. Finish Tool 触发 FINISHED 状态

**文件**: `openhands/sdk/agent/agent.py:411-412`

```python
# 执行工具后的状态设置
if tool.name == FinishTool.name:
    state.agent_status = AgentExecutionStatus.FINISHED  # ✅ 关键！
```

**流程**:
```
Agent 调用 finish 工具
  ↓
AgentBase._execute_one_action() 执行
  ↓
检测到 tool.name == "finish"
  ↓
设置 state.agent_status = FINISHED
  ↓
Conversation.run() 检测到 FINISHED
  ↓
停止循环，任务完成
```

### 3. 另一种触发 FINISHED 的方式

**文件**: `openhands/sdk/agent/agent.py:250-252`

```python
# 当 LLM 只返回消息（无工具调用）时
else:
    logger.info("LLM produced a message response - awaits user input")
    state.agent_status = AgentExecutionStatus.FINISHED
    msg_event = MessageEvent(source="agent", llm_message=message)
    on_event(msg_event)
```

**说明**:
- LLM 返回纯文本消息（无工具调用）→ 设置为 FINISHED
- 等待用户下一轮输入
- **不适用于单轮模式或自动化任务**

## mcpbench_dev 当前实现

### 1. Finish Tool 的可用性

**文件**: `utils/roles/task_agent.py:545-551`

```python
self.agent = OpenHandsAgent(
    llm=self.llm,
    tools=all_toolspecs,  # 传入 ToolSpec 列表
    agent_context=context,
    # ❌ 之前被注释掉了：
    # filter_tools_regex="^(?!think|finish).*$",  # 过滤掉 think 和 finish 工具
)
```

**状态**:
- ✅ `finish` 工具**现在可用**（filter 被注释掉）
- ✅ 已修复 `kind` 字段问题（通过 AgentContext 添加说明）

### 2. 任务循环的停止逻辑

**文件**: `utils/roles/task_agent.py:780-799`

```python
# 主循环中的停止检查
while self.stats["interaction_turns"] < max_turns:
    # ... 运行一轮交互 ...

    # ✅ 检查 1: OpenHands 状态
    if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
        self._debug_print("Agent finished execution")
        break  # 正确！如果 agent 调用了 finish，会在这里退出

    # ✅ 检查 2: 自定义终止条件
    if last_agent_message:
        recent_tool_calls = [...]  # 从事件提取工具调用
        if self.termination_checker(last_agent_message, recent_tool_calls, 'agent'):
            self._debug_print("Termination condition met by agent response")
            break
```

**逻辑**:
1. **检查 OpenHands 状态**: 如果 `agent_status == FINISHED`，退出循环
2. **检查自定义条件**: 调用 `termination_checker` 检查工具调用

### 3. Termination Checker 的实现

**文件**: `utils/task_runner/termination_checkers.py`

```python
def default_termination_checker(
    content: str,
    recent_tools: List[Dict],
    check_target: str = "user",
    user_stop_phrases: List[str] = [],
    agent_stop_tools: List[str] = [],  # ← 关键参数
):
    if check_target == "user":
        for stop_phrase in user_stop_phrases:
            if stop_phrase in content:
                return True
    elif check_target == "agent":
        for tool in recent_tools:
            if tool['function']['name'] in agent_stop_tools:  # ✅ 检查工具名
                return True
    return False
```

**配置**: `utils/data_structures/task_config.py:127-128`

```python
@classmethod
def build(cls, stop_conditions: Dict):
    # ...
    tool_names = stop_conditions.get("tool_names", ['local-claim_done'])  # ← 默认值
    return cls(user_phrases=user_phrases, tool_names=tool_names)
```

**默认停止工具**: `['local-claim_done']`

### 4. TaskRunner 的配置

**文件**: `utils/task_runner/runner.py:59`

```python
task_agent = TaskAgent(
    # ...
    termination_checker=partial(
        default_termination_checker,
        user_stop_phrases=task_config.stop.user_phrases,  # ["#### STOP"]
        agent_stop_tools=task_config.stop.tool_names,     # ['local-claim_done']
    ),
    # ...
)
```

## 问题分析

### 问题 1: Finish Tool 未被列为停止工具

**当前配置**:
```python
agent_stop_tools = ['local-claim_done']  # ❌ 不包含 'finish'
```

**问题**:
- `finish` 工具调用后，虽然 `agent_status` 被设置为 `FINISHED`
- 但如果在 `conversation.run()` 内部完成，可能不会立即被外层循环检测到
- **依赖 OpenHands 内部状态传播**

**正确配置**:
```python
agent_stop_tools = ['local-claim_done', 'finish']  # ✅ 添加 'finish'
```

### 问题 2: 双重停止机制的混淆

**当前有两个并行的停止机制**:

1. **OpenHands 内部**: 调用 `finish` → `agent_status = FINISHED`
2. **mcpbench_dev 自定义**: 检查 `agent_stop_tools` → `termination_checker` 返回 True

**混淆点**:
- 如果只依赖机制 1，需要确保外层循环正确检测 `agent_status`
- 如果只依赖机制 2，需要在 `agent_stop_tools` 中包含 `finish`
- **当前两者都有，但不协调**

### 问题 3: Local Tools 中没有 'local-claim_done'

**检查**:

```bash
# 搜索 local-claim_done 工具的定义
grep -r "local-claim_done" utils/local_tools/
```

**可能结果**: 没有找到！

**问题**:
- 默认配置期望 `local-claim_done` 工具
- 但该工具可能**不存在**或**未注册**
- 导致 agent 无法通过自定义停止条件结束任务

### 问题 4: 状态检查的时机

**文件**: `utils/roles/task_agent.py:752-760`

```python
# 3. 运行 Conversation（同步调用）
try:
    self.conversation.run()  # ← 在这里面，finish 可能被调用
except Exception as e:
    # ...
    raise

# 4. 提取新事件
new_events = self.conversation.state.events[events_before:]

# ... 处理事件 ...

# 7. 检查终止条件（在这里检查 agent_status）
if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
    self._debug_print("Agent finished execution")
    break  # ✅ 这里能正确检测到
```

**分析**:
- ✅ `conversation.run()` 执行完后，`agent_status` 已经被设置
- ✅ 第 782 行的检查能正确检测到 `FINISHED` 状态
- ✅ **这个机制应该是正常工作的**

## 实际问题根源

### 根本原因推测

基于以上分析，可能的问题是：

1. **Agent 没有调用 finish 工具**
   - LLM 不知道何时应该调用 `finish`
   - System prompt 中没有明确说明任务完成时应调用 `finish`
   - Agent 继续运行直到达到 `max_turns`

2. **Finish 工具可能仍然被过滤**
   - 检查实际运行时的工具列表
   - 确认 `finish` 工具是否真的可用

3. **LLM 调用 finish 失败**
   - `kind` 字段问题可能仍然存在
   - 需要验证修复是否生效

## 解决方案

### 方案 1: 在 System Prompt 中明确说明 finish 工具的使用（推荐）

**修改**: `utils/roles/task_agent.py:525-542`

```python
context = AgentContext(
    system_message_suffix="""
<CRITICAL_TOOL_USAGE_RULES>
IMPORTANT: When calling tools, DO NOT manually provide the 'kind' field.
The 'kind' field is automatically managed by the system and should NEVER be included in your tool call arguments.

Correct tool usage:
- think tool: {"thought": "your reasoning and analysis"}
- finish tool: {"message": "task completion summary"}

Incorrect usage (will cause validation errors):
- {"kind": "planning", "thought": "..."}  ❌ WRONG
- {"kind": "success", "message": "..."}   ❌ WRONG

The 'kind' field may appear in tool schemas but is SYSTEM-MANAGED ONLY.
Never include it in your tool call arguments.
</CRITICAL_TOOL_USAGE_RULES>

<TASK_COMPLETION_PROTOCOL>
CRITICAL: When you have completed the task, you MUST call the 'finish' tool to signal completion.

The finish tool usage:
- Parameters: {"message": "summary of what was accomplished"}
- Call this when: You have successfully completed the user's requested task
- Do NOT rely on: Max turns, timeouts, or implicit completion

Example:
When you have finished creating the report, uploading the files, or completing the analysis,
immediately call: finish(message="Task completed successfully. Created report.pdf with 5 sections covering all requested topics.")

Without calling finish, the system will not recognize task completion and may timeout.
</TASK_COMPLETION_PROTOCOL>
"""
)
```

### 方案 2: 添加 finish 到停止工具列表

**修改**: `utils/data_structures/task_config.py:127-128`

```python
@classmethod
def build(cls, stop_conditions: Dict):
    if stop_conditions is None:
        stop_conditions = {}
    if "user_phrases" in stop_conditions:
        user_phrases = stop_conditions["user_phrases"]
    else:
        user_phrases = ["#### STOP"]
    if "tool_names" in stop_conditions:
        tool_names = stop_conditions["tool_names"]
    else:
        tool_names = ['local-claim_done', 'finish']  # ✅ 添加 'finish'
    return cls(user_phrases=user_phrases, tool_names=tool_names)
```

**优点**: 双重保险，既检查 `agent_status` 也检查工具调用

### 方案 3: 移除 local-claim_done 依赖

如果 `local-claim_done` 工具不存在，改为：

```python
tool_names = ['finish']  # 只使用 OpenHands 的 builtin tool
```

### 方案 4: 创建 local-claim_done 工具（如果需要）

**创建**: `utils/local_tools/claim_done.py`

```python
from openhands.sdk.tool import Tool, ToolSpec
from openhands.sdk.tool.schema import ActionBase, ObservationBase
from pydantic import Field

class ClaimDoneAction(ActionBase):
    """Claim that the task is done."""
    message: str = Field(description="Summary of task completion")

class ClaimDoneTool(Tool[ClaimDoneAction, ObservationBase]):
    name = "local-claim_done"
    description = "Signal that the task has been completed successfully"

    def executor(self, action: ClaimDoneAction) -> ObservationBase:
        return ObservationBase(
            message=f"Task marked as complete: {action.message}",
            extra={"success": True}
        )

# 导出 ToolSpec
CLAIM_DONE_TOOL_SPEC = ToolSpec(
    name="local-claim_done",
    module_path="utils.local_tools.claim_done",
    class_name="ClaimDoneTool",
)
```

## 验证和测试

### 1. 检查 finish 工具是否可用

```python
cd /ssddata/mcpbench/wenshuo/scaffold/mcpbench_dev && uv run python -c "
from utils.task_runner.runner import TaskRunner
from utils.data_structures.task_config import TaskConfig
import json

# 加载一个任务配置
task_config_path = 'tasks/examples/github-example/task_config.json'
with open(task_config_path) as f:
    config = json.load(f)

task_config = TaskConfig.from_dict(config)

# 检查停止工具
print('Stop tool names:', task_config.stop.tool_names)

# TODO: 检查实际注册的工具列表
"
```

### 2. 测试 finish 工具调用

创建简单测试任务：

```json
{
  "task_str": "Please call the finish tool with a test message.",
  "max_turns": 5,
  "stop_conditions": {
    "tool_names": ["finish"]
  }
}
```

运行并检查：
- Agent 是否调用了 `finish` 工具
- `agent_status` 是否被设置为 `FINISHED`
- 任务是否正确结束（而非达到 max_turns）

### 3. 监控日志

在运行时查看：
```
Agent finished execution  # ← 应该看到这条消息
```

而不是：
```
Maximum turns (100) reached  # ← 不应该达到这里
```

## 推荐实施步骤

### 短期修复（立即实施）

1. **修改 system prompt**（方案 1）
   - 在 `AgentContext.system_message_suffix` 中添加 `<TASK_COMPLETION_PROTOCOL>`
   - 明确告诉 LLM 何时以及如何调用 `finish` 工具

2. **添加 finish 到停止工具**（方案 2）
   - 修改 `StopConditions.build()`，默认包含 `['finish']`

3. **验证修复**
   - 运行测试任务
   - 确认 agent 正确调用 `finish` 工具

### 长期改进

1. **统一停止机制**
   - 决定是依赖 OpenHands 的 `agent_status` 还是自定义 `termination_checker`
   - 简化逻辑，避免混淆

2. **改进 evaluation 逻辑**
   - 实施 MAX_TURNS_ANALYSIS.md 中的建议
   - 对超过 max_turns 的任务也运行 evaluation

3. **添加监控和统计**
   - 记录任务完成方式（finish tool vs max turns vs stop condition）
   - 分析哪些任务没有正确使用 `finish` 工具

## 总结

**问题本质**:
- ✅ OpenHands 的 `finish` 工具机制是完整的
- ✅ mcpbench_dev 的检测逻辑也是正确的（第 782 行）
- ❌ **但 LLM 不知道何时应该调用 `finish` 工具**
- ❌ System prompt 中没有明确的任务完成协议

**解决方案**:
1. 在 system prompt 中添加明确的 `<TASK_COMPLETION_PROTOCOL>`
2. 将 `finish` 添加到默认停止工具列表
3. 移除或实现 `local-claim_done` 工具

**预期效果**:
- ✅ Agent 主动调用 `finish` 工具结束任务
- ✅ 任务在完成后立即结束，不会达到 max_turns
- ✅ 更清晰的任务完成语义
- ✅ 更准确的评估结果
