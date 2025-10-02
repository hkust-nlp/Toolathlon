# OpenHands 统计系统重构完成报告

## 问题背景

在集成 OpenHands SDK 过程中，发现代码**混合了两种逻辑**：

1. **OpenHands SDK 的逻辑** - `conversation.state` 自动管理统计信息
2. **原框架的逻辑** - 手动维护 `self.stats` 字典和 `self.usage` 对象

这导致了一系列问题：
- `KeyError: 'cumulative_tool_calls'` - 初始化时遗漏字段
- `AttributeError: 'MessageEvent' object has no attribute 'content'` - 使用错误的 API
- `AttributeError: 'ObservationEvent' object has no attribute 'is_error'` - 访问不存在的属性
- 数据同步问题和代码复杂度增加

## 核心原则

**单一数据源（Single Source of Truth）**：

- **运行时**：OpenHands SDK 的 `conversation.state` 是唯一的统计数据源
- **兼容性**：仅在需要时（如保存结果）从 `conversation.state` 提取并转换为原框架格式

## 重构内容

### 1. 修复 MessageEvent 访问错误

**问题**：
```python
# ❌ 错误的访问方式（在两个地方）
# 位置1: _on_event 回调
content = event.content[0].text if event.content else ""

# 位置2: run_interaction_loop 提取最后一条消息
content = event.content[0].text if event.content else ""
```

**原因**：`MessageEvent` 没有 `content` 属性，而是有 `llm_message` 属性

**修复**：
```python
# ✅ 创建辅助方法
@staticmethod
def _extract_text_from_message_event(event: MessageEvent) -> str:
    """
    从 MessageEvent 提取文本内容

    MessageEvent.llm_message.content 是 List[TextContent | ImageContent]
    """
    text_parts = []
    for content_item in event.llm_message.content:
        if hasattr(content_item, 'text'):
            text_parts.append(content_item.text)
    return "".join(text_parts)

# 使用辅助方法
content = self._extract_text_from_message_event(event)
```

**修复位置**：
- 辅助方法定义：`task_agent.py:655-666`
- 在 `_on_event` 中使用：`task_agent.py:580`
- 在 `run_interaction_loop` 中使用：`task_agent.py:743`

### 2. 修复 ObservationEvent 错误处理

**问题**：
```python
# ❌ 错误：ObservationEvent 没有 is_error 属性
if event.is_error:
    print_color(f"[Observation Error]", "red")
```

**原因**：OpenHands SDK 使用不同的事件类型表示错误：
- `ObservationEvent` - 正常工具执行结果
- `AgentErrorEvent` - 代理/脚手架错误
- `UserRejectObservation` - 用户拒绝操作

**修复**：
```python
# ✅ 正确的错误处理
elif isinstance(event, ObservationEvent):
    # 正常工具结果
    if self.debug:
        content = str(event.observation.to_llm_content)
        print_color(f"[Observation] {event.tool_name}: {content[:100]}", "green")

elif isinstance(event, (AgentErrorEvent, UserRejectObservation)):
    # 错误或拒绝
    if self.debug:
        if isinstance(event, AgentErrorEvent):
            print_color(f"[Agent Error] {event.error}", "red")
        else:
            print_color(f"[User Reject] {event.rejection_reason}", "red")
```

**位置**：`task_agent.py:601-615`

### 3. 重构 _on_event 回调

**原则**：`_on_event` 只用于：
1. 维护 `logs_to_record`（用于最终保存）
2. 调试输出
3. **不再**手动更新统计信息

**之前**：
```python
# ❌ 手动更新统计信息
elif isinstance(event, ActionEvent):
    self.stats["cumulative_tool_calls"] += 1
    if self.debug:
        print_color(f"[Action] {event.tool_name}", "cyan")
```

**之后**：
```python
# ✅ 只做调试输出，统计由 OpenHands 管理
elif isinstance(event, ActionEvent):
    # 注意：不再手动更新 self.stats，统计信息由 OpenHands conversation.state 管理
    if self.debug:
        print_color(f"[Action] {event.tool_name}", "cyan")
```

**位置**：`task_agent.py:565-622`

### 4. 创建统计信息提取方法

创建了 `_extract_stats_from_conversation()` 方法，作为从 OpenHands 单一数据源提取统计信息的桥梁。

```python
def _extract_stats_from_conversation(self) -> None:
    """
    从 conversation.state 提取统计信息到 self.stats 和 self.usage

    这个方法用于兼容性 - 在需要时从 OpenHands 的单一数据源提取信息
    """
    if not self.conversation or not hasattr(self.conversation, 'state'):
        return

    # 获取 OpenHands 的统计信息
    metrics = self.conversation.state.stats.get_combined_metrics()

    # 更新 self.usage（兼容性）
    if metrics.accumulated_token_usage:
        self.usage.input_tokens = metrics.accumulated_token_usage.prompt_tokens
        self.usage.output_tokens = metrics.accumulated_token_usage.completion_tokens
        self.usage.requests = len(metrics.costs)

    # 更新 self.stats（兼容性）
    self.stats["total_tokens"] = self.usage.input_tokens + self.usage.output_tokens
    self.stats["input_tokens"] = self.usage.input_tokens
    self.stats["output_tokens"] = self.usage.output_tokens
    self.stats["agent_llm_requests"] = self.usage.requests

    # 从事件中统计工具调用次数
    if hasattr(self.conversation.state, 'events'):
        action_events = [e for e in self.conversation.state.events if isinstance(e, ActionEvent)]
        self.stats["cumulative_tool_calls"] = len(action_events)
        self.stats["tool_calls"] = len(action_events)
```

**位置**：`task_agent.py:624-653`

### 5. 更新调用点

在所有需要统计信息的地方调用 `_extract_stats_from_conversation()`：

#### a) run_interaction_loop 结束时
```python
# 从 conversation.state 提取最终统计信息（单一数据源）
self._extract_stats_from_conversation()
```
**位置**：`task_agent.py:792-793`

#### b) get_cost_summary 开始时
```python
def get_cost_summary(self) -> Tuple[Dict, Dict]:
    """获取成本摘要（从 OpenHands conversation.state 提取）"""
    # 确保统计信息是最新的
    self._extract_stats_from_conversation()
    # ...
```
**位置**：`task_agent.py:795-798`

#### c) save_results 开始时
```python
async def save_results(self) -> None:
    """
    保存运行结果到日志文件（OpenHands 版本）

    统计信息来源：
    - self.stats 和 self.usage: 通过 _extract_stats_from_conversation() 从 conversation.state 提取
    - session_stats: 直接从 conversation.state.events 计算
    - logs_to_record: 在 _on_event 回调中维护
    """
    # 确保统计信息是最新的
    self._extract_stats_from_conversation()
    # ...
```
**位置**：`task_agent.py:821-831`

## OpenHands 统计系统架构

### 数据结构层次

```
conversation.state (ConversationState)
  └── stats (ConversationStats)
      └── service_to_metrics: Dict[str, Metrics]
          └── Metrics (per LLM service)
              ├── accumulated_cost: float
              ├── costs: List[Cost]
              ├── response_latencies: List[ResponseLatency]
              ├── token_usages: List[TokenUsage]
              └── accumulated_token_usage: TokenUsage
                  ├── prompt_tokens: int
                  ├── completion_tokens: int
                  ├── cache_read_tokens: int
                  ├── cache_write_tokens: int
                  └── reasoning_tokens: int
```

### 获取统计信息的方法

```python
# 获取合并的统计信息（所有 LLM 服务）
metrics = conversation.state.stats.get_combined_metrics()

# 访问 token 使用
total_input = metrics.accumulated_token_usage.prompt_tokens
total_output = metrics.accumulated_token_usage.completion_tokens

# 访问成本
total_cost = metrics.accumulated_cost

# 访问请求数
total_requests = len(metrics.costs)
```

## 架构对比

| 组件 | 之前（错误的混合逻辑） | 之后（单一数据源） |
|------|---------------------|------------------|
| **统计来源** | 手动在 `_on_event` 中更新 | `conversation.state` 自动跟踪 |
| **`self.stats`** | 在事件回调中递增 | 仅在需要时从 `conversation.state` 提取 |
| **`self.usage`** | 手动累加 | 从 `Metrics.accumulated_token_usage` 提取 |
| **工具调用统计** | 手动计数器 | 从 `events` 过滤 `ActionEvent` |
| **`_on_event` 职责** | 日志 + 统计更新 | 仅日志和调试输出 |
| **数据同步** | 容易出错（两个数据源） | 无同步问题（单一数据源） |

## 兼容性保留

为了与现有系统兼容，保留了以下内容：

1. **`self.stats` 字典** - 用于 eval 系统和日志记录
2. **`self.usage` 对象** - 用于成本计算
3. **`self.logs_to_record`** - 用于保存对话历史

**但是**：这些数据结构现在只在需要时从 `conversation.state` 填充，不再在运行时手动维护。

## 修复的错误

### 错误 1: KeyError: 'cumulative_tool_calls'
- **原因**：`self.stats` 初始化时遗漏了 `cumulative_tool_calls` 键
- **修复**：添加键到初始化，并在 `_extract_stats_from_conversation()` 中从事件计算

### 错误 2: AttributeError: 'MessageEvent' object has no attribute 'content'
- **原因**：使用了错误的 API，应该是 `event.llm_message.content`
- **修复**：正确访问 `MessageEvent.llm_message.content`

### 错误 3: AttributeError: 'ObservationEvent' object has no attribute 'is_error'
- **原因**：OpenHands 使用不同的事件类型表示错误
- **修复**：分别处理 `ObservationEvent`, `AgentErrorEvent`, `UserRejectObservation`

## 受益

1. ✅ **单一数据源** - 所有统计信息来自 `conversation.state`
2. ✅ **无同步问题** - 不会出现手动计数器与实际不一致的情况
3. ✅ **更简洁的代码** - `_on_event` 不再负责统计更新
4. ✅ **更准确的统计** - 直接从 OpenHands LLM 层获取 token 使用
5. ✅ **更容易维护** - 减少了手动管理状态的代码
6. ✅ **完全遵循 OpenHands SDK 设计** - 不再混合两种逻辑

## 数据流

### 运行时数据流

```
LLM 调用
   ↓
OpenHands SDK (自动跟踪)
   ↓
conversation.state.stats.service_to_metrics
   ↓
[不更新 self.stats 和 self.usage]
```

### 保存结果时数据流

```
需要保存结果
   ↓
调用 _extract_stats_from_conversation()
   ↓
从 conversation.state.stats 读取
   ↓
填充 self.stats 和 self.usage
   ↓
保存到 log.json
```

## 文件修改摘要

**文件**：`utils/roles/task_agent.py`

**修改行数**：
- 修改：~60 行
- 新增：~30 行（`_extract_stats_from_conversation` 方法）

**修改的方法**：
1. `_on_event()` - 移除统计更新，修复 API 访问
2. `_extract_stats_from_conversation()` - 新增
3. `run_interaction_loop()` - 在结束时调用统计提取
4. `get_cost_summary()` - 在开始时调用统计提取
5. `save_results()` - 在开始时调用统计提取，添加文档

## 测试建议

1. **基本功能测试**：
   ```bash
   uv run demo.py \
     --eval_config scripts/debug_eval_config.json \
     --task_dir debug/debug-task \
     --debug
   ```

2. **验证统计准确性**：
   - 检查 `log.json` 中的 `key_stats`
   - 对比 OpenHands 的 `conversation.state.stats`
   - 确认 token 使用和工具调用次数正确

3. **验证事件处理**：
   - 观察调试输出中的事件信息
   - 确认 MessageEvent、ActionEvent、ObservationEvent 都正确处理
   - 测试错误情况（AgentErrorEvent）

## 下一步

- ✅ 重构完成
- ⏳ 运行测试验证
- ⏳ 监控生产环境，确保无回归

---

**重构完成时间**：2025-10-02
**重构原因**：完全遵循 OpenHands SDK 的设计原则，使用单一数据源
**核心改进**：从混合逻辑迁移到纯 OpenHands SDK 架构
