# mcpbench_dev - Builtin Tools "kind" 字段问题修复记录

## 修复日期
2025-10-04

## 问题描述
Agent 在调用 `think` 和 `finish` 工具时出现验证错误：

```
[Agent Error] think: Error validating args {"kind":"planning","thought":"..."}
for tool 'think': 1 validation error for ThinkAction
kind
  Input should be 'ThinkAction' [type=literal_error, input_value='planning', input_type=str]
```

## 根本原因
1. OpenHands SDK 的所有 `ActionBase` 子类都自动包含 `kind` 字段（用于内部类型判别）
2. 在转换为 OpenAI tool schema 时，`kind` 字段被错误地暴露给 LLM
3. LLM 看到这个字段并尝试填写，导致验证失败（期望值为类名如 "ThinkAction"，实际收到 "planning" 等）

## 实施的修复方案

### 方案：在 System Prompt 中添加明确说明

**修改文件**: `utils/roles/task_agent.py`

**修改位置**: `setup_agent` 方法中创建 OpenHandsAgent 之前（第 521-551 行）

**修改内容**:

```python
# 创建 AgentContext 添加 builtin tools 使用说明（修复 kind 字段问题）
from openhands.sdk.context import AgentContext

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
"""
)

self.agent = OpenHandsAgent(
    llm=self.llm,
    tools=all_toolspecs,
    agent_context=context,  # 添加工具使用说明
)
```

## 修复效果

### 预期改进
1. ✅ LLM 在 system prompt 中看到明确的指令，不再填写 `kind` 字段
2. ✅ `think` 和 `finish` 工具可以正常使用
3. ✅ 保留了 OpenHands SDK 的完整默认 system prompt（9500+ 字符）
4. ✅ 不需要修改 OpenHands SDK 源代码

### 验证测试

```bash
cd /ssddata/mcpbench/wenshuo/scaffold/mcpbench_dev

# 验证 system message 包含了新的规则
uv run python -c "
from openhands.sdk.agent.agent import Agent as OpenHandsAgent
from openhands.sdk.context import AgentContext
from openhands.sdk import LLM
from pydantic import SecretStr

context = AgentContext(system_message_suffix='<CRITICAL_TOOL_USAGE_RULES>test</CRITICAL_TOOL_USAGE_RULES>')
llm = LLM(model='gpt-4', api_key=SecretStr('test'))
agent = OpenHandsAgent(llm=llm, tools=[], agent_context=context)

assert '<CRITICAL_TOOL_USAGE_RULES>' in agent.system_message
print('✅ Verification passed')
"
```

## 长期改进建议

虽然当前修复可以工作，但建议向 OpenHands SDK 提交 PR 实施更彻底的修复：

### 建议修改 1: 排除 `kind` 字段
**文件**: `openhands/sdk/tool/schema.py`

在 `ActionBase.to_mcp_schema()` 中排除 `kind` 字段：

```python
@classmethod
def to_mcp_schema(cls) -> dict[str, Any]:
    """Convert to JSON schema format, excluding the 'kind' discriminator field."""
    full_schema = cls.model_json_schema()
    processed = _process_schema_node(full_schema, full_schema.get("$defs", {}))

    # 排除 'kind' 字段（LLM 不应该填写，会自动设置）
    if "properties" in processed and "kind" in processed["properties"]:
        del processed["properties"]["kind"]

    if "required" in processed and "kind" in processed["required"]:
        processed["required"].remove("kind")

    return processed
```

### 建议修改 2: 在默认 system prompt 中说明
**文件**: `openhands/sdk/agent/prompts/system_prompt.j2`

在文件末尾添加：

```jinja2
<TOOL_PARAMETER_GUIDELINES>
When calling tools, strictly follow the parameter schema provided.
Do not invent additional parameters.

Note: Some tool schemas may include a 'kind' field - this is system-managed.
Never manually provide the 'kind' parameter in your tool calls.
</TOOL_PARAMETER_GUIDELINES>
```

## 相关文档

详细分析文档：
- `/ssddata/mcpbench/wenshuo/scaffold/agent-sdk/KIND_FIELD_ISSUE_ANALYSIS.md`
- `/ssddata/mcpbench/wenshuo/scaffold/agent-sdk/BUILTIN_TOOLS_ANALYSIS.md`
- `/ssddata/mcpbench/wenshuo/scaffold/agent-sdk/SYSTEM_PROMPT_ANALYSIS.md`

## 回归测试

在测试时，确认以下场景：
1. ✅ Agent 可以成功调用 `think` 工具
2. ✅ Agent 可以成功调用 `finish` 工具
3. ✅ 不再出现 "kind" 字段验证错误
4. ✅ tool_use_id 匹配错误也应消失（这是 kind 错误的连带问题）

## 监控指标

建议监控以下指标以验证修复效果：
- Agent Error 中包含 "kind" 关键词的频率（应降至 0）
- `think` 工具调用成功率（应接近 100%）
- `finish` 工具调用成功率（应接近 100%）
- BadRequestError 中 "tool_use_id" 错误的频率（应大幅下降）

## 回滚方案

如果修复导致其他问题，可以回滚：

```python
# 移除 agent_context 参数
self.agent = OpenHandsAgent(
    llm=self.llm,
    tools=all_toolspecs,
    # agent_context=context,  # 注释掉这行
)
```

但注意：回滚后 `think` 和 `finish` 工具将无法正常使用，除非同时添加：

```python
filter_tools_regex="^(?!think|finish).*$",  # 过滤掉这两个工具
```
