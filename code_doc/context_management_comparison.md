# OpenHands vs mcpbench_dev 上下文管理深度对比分析

## 一、核心架构对比

### 1.1 mcpbench_dev 的上下文管理

#### 核心组件
```
ContextManagedRunner (继承 Runner)
├── shared_context (Dict)
│   ├── _agent_workspace
│   ├── _session_id
│   ├── _history_dir
│   ├── _context_meta (轮次统计)
│   └── _context_limit (token限制)
├── self.logs (List[Dict])  # 手动管理的消息历史
└── 历史文件管理 (JSONL格式)
```

#### 工作原理

**1. 上下文存储** (`task_agent.py:516-534`)
```python
self.shared_context = {
    "_agent_workspace": workspace_path,
    "_session_id": session_id,
    "_history_dir": history_dir,
    "_context_meta": {
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "current_turn": -1,
        "total_turns_ever": 0,
        "turns_in_current_sequence": 0,
        "mini_turns_in_current_sequence": 0,
        "boundary_in_current_sequence": [],  # 轮次边界
        "truncated_turns": 0,
        "truncation_history": []
    },
    "_context_limit": get_context_window(model_name)
}
```

**2. 历史管理** (`context_managed_runner.py:458-485`)
- 使用 JSONL 文件持久化
- 每个轮次的每个 item 独立保存
- 包含详细的元数据（turn, timestamp, agent, item_type）

```python
def _save_items_to_history(
    session_id: str,
    turn_number: int,
    items: List[RunItem],
    agent_name: str,
    history_dir: Path
):
    history_path = history_dir / f"{session_id}_history.jsonl"
    with open(history_path, 'a', encoding='utf-8') as f:
        for step_idx, item in enumerate(items):
            record = {
                "in_turn_steps": step_idx,
                "turn": turn_number,
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "item_type": item.type,
                "raw_content": item.raw_item.model_dump()
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
```

**3. 上下文截断** (`context_managed_runner.py:290-365`)
- 多种截断策略：
  - `keep_recent_turns`: 保留最近N轮
  - `keep_recent_percent`: 保留最近X%
  - `delete_first_turns`: 删除最前面N轮
  - `delete_first_percent`: 删除最前面X%

```python
def _handle_truncation(
    original_input, pre_step_items, new_step_items,
    truncate_params, context_wrapper
):
    method = truncate_params.get("method")
    value = truncate_params.get("value")

    # 基于轮次边界进行截断
    turn_boundaries = context["_context_meta"]["boundary_in_current_sequence"]

    if method == "keep_recent_turns":
        keep_turns = min(int(value), total_turns)
    # ... 计算截断位置并删除
```

**4. 上下文重置** (`task_agent.py:178-235`)
- 触发条件：`ContextTooLongError`
- 保留累积信息（总轮数、截断历史）
- 清空当前序列的历史
- 生成摘要消息重新开始

```python
def _reset_context_and_history(self):
    # 保存关键信息
    session_id = self.shared_context.get("_session_id")
    current_turn = meta.get("current_turn", 0)
    total_turns_ever = meta.get("total_turns_ever", 0)
    truncated_turns = meta.get("truncated_turns", 0)

    # 重置 shared_context
    self.shared_context = {
        "_agent_workspace": agent_workspace,
        "_session_id": session_id,
        "_context_meta": {
            "current_turn": current_turn,  # 保留
            "total_turns_ever": total_turns_ever,  # 保留
            "turns_in_current_sequence": 0,  # 重置
            "truncated_turns": truncated_turns + turns_deleted,
            "truncation_history": new_history,
            "context_reset": True
        }
    }

    # 清空 logs
    self.logs = []
```

**5. 上下文溢出处理流程** (`task_agent.py:652-742`)
```python
try:
    result = await ContextManagedRunner.run(
        starting_agent=self.agent,
        input=self.logs,
        context=self.shared_context,
        max_turns=remaining_steps,
    )
except ContextTooLongError as e:
    # 1. 提取已执行的步数
    executed_steps = self.shared_context["_force_reset_context"]["executed_turns"]

    # 2. 累计步数
    self.cumulative_inner_steps += executed_steps

    # 3. 检查是否还有剩余步数
    if self.cumulative_inner_steps >= max_inner_steps:
        raise RuntimeError("No remaining steps")

    # 4. 重置上下文
    self._reset_context_and_history()

    # 5. 获取历史摘要
    history_summary = ContextManagedRunner.get_recent_turns_summary(
        self.history_dir, self.session_id, num_turns=10
    )

    # 6. 构建新的用户查询
    new_user_query = (
        "[Context reset] Previous context exceeded limit. "
        f"Original task: {first_user_input}\n\n{history_summary}"
    )

    # 7. 重新开始
    self.logs = [{"role": "user", "content": new_user_query}]
    # 继续循环
```

### 1.2 OpenHands SDK 的上下文管理

#### 核心组件
```
ConversationState
├── events (EventLog - 文件支持的事件列表)
├── agent (AgentBase)
├── persistence_dir (持久化目录)
├── stats (ConversationStats - token统计)
└── FIFOLock (线程安全)

Agent + Condenser
├── condenser (CondenserBase - 可选)
│   ├── LLMSummarizingCondenser
│   ├── PipelineCondenser
│   └── NoOpCondenser
└── agent_context (AgentContext)
    ├── microagents (动态上下文注入)
    └── system/user message suffixes
```

#### 工作原理

**1. 事件驱动存储** (`conversation/state.py`)
```python
class ConversationState(OpenHandsModel, FIFOLock):
    id: ConversationID
    agent: AgentBase
    working_dir: str
    persistence_dir: str | None

    # 私有属性
    _events: EventLog  # 文件支持的事件列表
    _fs: FileStore
    _secrets_manager: SecretsManager

    @property
    def events(self) -> ListLike[EventBase]:
        return self._events  # 返回列表式接口
```

**2. EventLog - 基于文件的事件存储** (`conversation/event_store.py`)
```python
class EventLog(ListLike[EventBase]):
    def __init__(self, fs: FileStore, dir_path: str = EVENTS_DIR):
        self._fs = fs
        self._dir = dir_path
        self._id_to_idx: dict[EventID, int] = {}
        self._idx_to_id: dict[int, EventID] = {}
        self._length = self._scan_and_build_index()

    def append(self, item: EventBase) -> None:
        # 每个事件保存为独立文件
        path = f"{self._dir}/{idx:06d}_{event_id}.json"
        self._fs.write(path, item.model_dump_json())
        self._length += 1

    def __getitem__(self, idx: int) -> EventBase:
        # 按需从文件加载
        txt = self._fs.read(self._path(idx))
        return EventBase.model_validate_json(txt)
```

**文件格式**:
```
persistence_dir/
├── base_state.json          # 基本状态快照
└── events/
    ├── 000000_evt-uuid1.json
    ├── 000001_evt-uuid2.json
    └── 000002_evt-uuid3.json
```

**3. View 机制 - 事件到 LLM 消息的转换** (`context/view.py`)
```python
class View(BaseModel):
    events: list[LLMConvertibleEvent]
    unhandled_condensation_request: bool = False
    condensations: list[Condensation] = []

    @staticmethod
    def from_events(events: ListLike[EventBase]) -> "View":
        """从事件列表创建视图，处理压缩语义"""
        forgotten_event_ids: set[EventID] = set()
        condensations: list[Condensation] = []

        # 1. 收集所有 Condensation 事件
        for event in events:
            if isinstance(event, Condensation):
                condensations.append(event)
                forgotten_event_ids.update(event.forgotten_event_ids)
                forgotten_event_ids.add(event.id)  # 也忘记压缩事件本身

        # 2. 过滤掉被遗忘的事件
        kept_events = [
            event for event in events
            if event.id not in forgotten_event_ids
            and isinstance(event, LLMConvertibleEvent)
        ]

        # 3. 插入摘要（如果有）
        if summary and summary_offset:
            summary_event = CondensationSummaryEvent(summary=summary)
            kept_events.insert(summary_offset, summary_event)

        return View(events=kept_events, condensations=condensations)
```

**4. Condenser - 自动压缩历史** (`context/condenser/llm_summarizing_condenser.py`)
```python
class LLMSummarizingCondenser(RollingCondenser):
    llm: LLM
    max_size: int = 120  # 最大事件数
    keep_first: int = 4   # 保留前N个事件

    def should_condense(self, view: View) -> bool:
        # 触发条件：事件数超过 max_size 或有未处理的压缩请求
        if view.unhandled_condensation_request:
            return True
        return len(view) > self.max_size

    def get_condensation(self, view: View) -> Condensation:
        head = view[:self.keep_first]
        target_size = self.max_size // 2
        events_from_tail = target_size - len(head) - 1

        # 识别要遗忘的事件
        forgotten_events = view[self.keep_first : -events_from_tail]

        # 使用 LLM 生成摘要
        event_strings = [str(e) for e in forgotten_events]
        prompt = render_template(
            "summarizing_prompt.j2",
            previous_summary=previous_summary,
            events=event_strings,
        )

        llm_response = self.llm.completion(messages=[prompt])
        summary = llm_response.message.content[0].text

        return Condensation(
            forgotten_event_ids=[e.id for e in forgotten_events],
            summary=summary,
            summary_offset=self.keep_first,
        )
```

**5. Agent 中的压缩集成** (`agent/agent.py:145-196`)
```python
def step(self, state: ConversationState, on_event):
    # 如果配置了 condenser，先尝试压缩
    if self.condenser is not None:
        view = View.from_events(state.events)
        condensation_result = self.condenser.condense(view)

        match condensation_result:
            case View():
                # 直接使用视图
                llm_convertible_events = condensation_result.events
            case Condensation():
                # 需要执行压缩，添加压缩事件
                on_event(condensation_result)
                return None  # 不执行这一步，等下一轮

    # 正常的 LLM 调用
    try:
        llm_response = self.llm.completion(
            messages=_messages,
            tools=list(self.tools_map.values()),
        )
    except Exception as e:
        # 如果是上下文窗口超出错误且有 condenser
        if (self.condenser is not None
            and self.condenser.handles_condensation_requests()
            and self.llm.is_context_window_exceeded_exception(e)):

            # 触发压缩请求
            on_event(CondensationRequest())
            return
        else:
            raise e
```

**6. 上下文窗口超出检测** (`llm/llm.py:883`)
```python
@staticmethod
def is_context_window_exceeded_exception(exception: Exception) -> bool:
    """检查异常是否为上下文窗口超出"""
    return isinstance(exception, ContextWindowExceededError)
```

**7. AgentContext - 动态上下文注入** (`context/agent_context.py`)
```python
class AgentContext(BaseModel):
    microagents: list[BaseMicroagent] = []
    system_message_suffix: str | None = None
    user_message_suffix: str | None = None

    def get_system_message_suffix(self) -> str | None:
        """获取系统消息后缀（包含 repo microagents）"""
        repo_microagents = [
            m for m in self.microagents
            if isinstance(m, RepoMicroagent)
        ]

        if repo_microagents:
            return render_template(
                "system_message_suffix.j2",
                repo_microagents=repo_microagents,
                system_message_suffix=self.system_message_suffix
            )
        return self.system_message_suffix

    def get_user_message_suffix(
        self, user_message: Message, skip_microagent_names: list[str]
    ) -> tuple[TextContent, list[str]] | None:
        """根据触发词动态注入知识"""
        query = extract_text(user_message)
        recalled_knowledge = []

        for microagent in self.microagents:
            if isinstance(microagent, KnowledgeMicroagent):
                trigger = microagent.match_trigger(query)
                if trigger and microagent.name not in skip_microagent_names:
                    recalled_knowledge.append(
                        MicroagentKnowledge(
                            name=microagent.name,
                            trigger=trigger,
                            content=microagent.content
                        )
                    )

        if recalled_knowledge:
            formatted_text = render_template(
                "microagent_knowledge_info.j2",
                triggered_agents=recalled_knowledge
            )
            return TextContent(text=formatted_text), [k.name for k in recalled_knowledge]

        return None
```

## 二、关键差异对比表

| 特性 | mcpbench_dev | OpenHands SDK |
|------|--------------|---------------|
| **存储方式** | 手动管理的 `self.logs` 列表 | `EventLog` - 文件支持的事件列表 |
| **历史格式** | JSONL (每行一个 item) | 每个事件独立 JSON 文件 |
| **上下文传递** | `shared_context` Dict | `ConversationState` 对象 |
| **压缩机制** | 手动截断 + 重置 | `Condenser` 自动压缩 |
| **触发方式** | 捕获 `ContextTooLongError` | LLM 异常 + 主动检查 |
| **压缩策略** | 基于轮次的截断（删除前N轮） | 基于事件的摘要（LLM生成） |
| **摘要生成** | 手动构建历史摘要字符串 | LLM 自动生成摘要事件 |
| **状态恢复** | 从 JSONL 重建 logs | 从文件系统加载事件 |
| **元数据跟踪** | `_context_meta` 字典 | `ConversationState` 字段 |
| **轮次边界** | 手动维护 `boundary_in_current_sequence` | 事件类型自然边界 |
| **持久化** | 自定义 JSONL + pickle 检查点 | 内置 FileStore + 自动保存 |
| **线程安全** | 无显式保护 | `FIFOLock` 保护 |

## 三、上下文溢出处理对比

### 3.1 mcpbench_dev 的处理流程

```
用户输入 → Agent 响应
    ↓
ContextManagedRunner.run()
    ↓
检测 token 数量
    ↓
抛出 ContextTooLongError
    ↓
外层捕获 (task_agent.py:652)
    ↓
1. 记录已执行步数
2. 累计到 cumulative_inner_steps
3. 检查是否还有剩余步数
4. 调用 _reset_context_and_history()
   - 清空 self.logs
   - 重置 shared_context["_context_meta"]["turns_in_current_sequence"]
   - 保留累积统计信息
5. 读取最近10轮历史摘要
6. 构建新的用户消息：
   "[Context reset] ... Original task: ... Recent history: ..."
7. 重新执行 Runner.run()
```

### 3.2 OpenHands SDK 的处理流程

```
用户消息 → Conversation.run()
    ↓
循环: Agent.step()
    ↓
如果配置了 condenser:
    ├─ View.from_events(state.events)
    ├─ condenser.condense(view)
    │   ├─ should_condense? (len > max_size)
    │   │   Yes → get_condensation()
    │   │        ├─ 选择要遗忘的事件
    │   │        ├─ LLM 生成摘要
    │   │        └─ 返回 Condensation 事件
    │   └─ No → 返回 View
    └─ 如果返回 Condensation:
        - on_event(condensation) → 添加到 state.events
        - return (不执行 LLM 调用)
        - 下一轮 Agent.step() 时:
          - View.from_events() 会自动：
            - 过滤掉 forgotten_event_ids
            - 插入摘要事件
          - 使用压缩后的 View

LLM 调用
    ↓
如果抛出 ContextWindowExceededError:
    ├─ 如果 condenser 支持 handles_condensation_requests():
    │   └─ on_event(CondensationRequest())
    │       - 标记需要压缩
    │       - return (不执行这一步)
    │       - 下一轮 Agent.step() 时强制压缩
    └─ 否则: 重新抛出异常
```

### 3.3 关键差异

| 方面 | mcpbench_dev | OpenHands SDK |
|------|--------------|---------------|
| **处理位置** | 外层循环捕获 | Agent.step() 内部处理 |
| **压缩时机** | 出错后被动响应 | 主动检查 + 异常响应 |
| **历史保留** | 完全清空当前序列 | 保留部分事件 + 摘要 |
| **摘要方式** | 字符串拼接历史 | LLM 生成自然语言摘要 |
| **恢复方式** | 新消息包含摘要 | 摘要作为事件插入历史 |
| **上下文连续性** | 断裂（显式重置标记） | 连续（摘要无缝衔接） |

## 四、替换实施方案

### 4.1 核心文件修改清单

#### 必须完全重写的文件

**1. `utils/roles/task_agent.py`** (最大改动)
- **现有行数**: ~987 行
- **预计改动**: ~500 行 (50%)
- **主要修改**:
  - 移除 `self.logs` 管理 → 使用 `conversation.state.events`
  - 移除 `shared_context` → 使用 `ConversationState`
  - 移除上下文重置逻辑 → 配置 `Condenser`
  - 修改 `run_interaction_loop` → 使用 `Conversation.run()`

**修改示例**:
```python
# === 移除 ===
self.logs: List[Dict] = []
self.shared_context: Dict = {}
self.cumulative_inner_steps = 0
self._reset_context_and_history()
self._handle_context_overflow()

# === 添加 ===
self.conversation: Conversation
self.condenser: CondenserBase

# === 修改前 ===
self.logs.append({"role": "user", "content": user_query})
result = await ContextManagedRunner.run(
    starting_agent=self.agent,
    input=self.logs,
    context=self.shared_context,
    max_turns=remaining_steps,
)
self.logs = self.build_new_logs(result.input, result.new_items)

# === 修改后 ===
self.conversation.send_message(user_query)
self.conversation.run()
agent_response = self._get_last_agent_message()
```

**2. `utils/roles/context_managed_runner.py`** (部分保留)
- **现有行数**: ~600 行
- **预计改动**: 改为工具函数库而非 Runner 子类
- **保留功能**:
  - 历史文件读写 (`_save_items_to_history`)
  - 历史摘要生成 (`get_recent_turns_summary`)
  - 历史格式转换
- **移除功能**:
  - `_run_single_turn` 重写
  - `_handle_truncation`
  - Runner 相关逻辑

**重构示例**:
```python
# === 改为独立工具类 ===
class HistoryManager:
    """历史记录管理工具"""

    @staticmethod
    def save_to_jsonl(session_id: str, turn: int,
                      events: List[EventBase], history_dir: Path):
        """保存事件到 JSONL（兼容旧格式）"""
        ...

    @staticmethod
    def get_recent_summary(history_dir: Path, session_id: str,
                           num_turns: int = 10) -> str:
        """获取最近N轮的摘要"""
        ...

    @staticmethod
    def convert_events_to_logs(events: List[EventBase]) -> List[Dict]:
        """将 OpenHands 事件转换为旧格式的 logs"""
        ...
```

#### 需要适配的文件

**3. `utils/general/helper.py`**
- **修改**: `build_agent_model_provider` → `build_llm_config`
- **行数**: ~50 行改动

```python
# === 修改前 ===
def build_agent_model_provider(agent_config: AgentConfig) -> ModelProvider:
    return ModelProvider(...)

# === 修改后 ===
def build_llm(agent_config: AgentConfig) -> LLM:
    return LLM(
        model=agent_config.model.real_name,
        api_key=SecretStr(get_api_key(agent_config)),
        base_url=agent_config.model.base_url,
        temperature=agent_config.generation.temperature,
        top_p=agent_config.generation.top_p,
        max_tokens=agent_config.generation.max_tokens,
    )
```

**4. `utils/task_runner/runner.py`**
- **修改**: 更新 `run_single_task` 调用接口
- **行数**: ~20 行改动

```python
# === 修改前 ===
agent_model_provider = build_agent_model_provider(agent_config)

task_agent = TaskAgent(
    agent_model_provider=agent_model_provider,
    ...
)

# === 修改后 ===
llm = build_llm(agent_config)

task_agent = TaskAgent(
    llm=llm,
    ...
)
```

#### 新增文件

**5. `utils/openhands_adapter/condenser_factory.py`** (新增)
- **功能**: 创建和配置 Condenser
- **行数**: ~150 行

```python
from openhands.sdk.context.condenser import (
    LLMSummarizingCondenser,
    NoOpCondenser
)
from utils.data_structures.agent_config import AgentConfig

class CondenserFactory:
    """Condenser 工厂类"""

    @staticmethod
    def create_condenser(
        agent_config: AgentConfig,
        llm: LLM,
        enable_condensation: bool = True
    ) -> CondenserBase:
        """创建 condenser"""

        if not enable_condensation:
            return NoOpCondenser()

        # 基于配置创建 LLM summarizing condenser
        return LLMSummarizingCondenser(
            llm=llm,
            max_size=agent_config.context.max_events or 120,
            keep_first=agent_config.context.keep_first_events or 4,
        )
```

**6. `utils/openhands_adapter/event_converter.py`** (新增)
- **功能**: OpenHands 事件 ↔ mcpbench_dev 格式转换
- **行数**: ~200 行

```python
from openhands.sdk.event import EventBase, MessageEvent, ActionEvent
from typing import List, Dict

class EventConverter:
    """事件格式转换器"""

    @staticmethod
    def events_to_logs(events: List[EventBase]) -> List[Dict]:
        """OpenHands 事件 → mcpbench_dev logs 格式"""
        logs = []
        for event in events:
            if isinstance(event, MessageEvent):
                logs.append({
                    "role": event.source,  # "user" or "agent"
                    "content": extract_text(event.llm_message)
                })
            elif isinstance(event, ActionEvent):
                logs.append({
                    "role": "assistant",
                    "content": extract_thought(event.thought),
                    "tool_calls": [{
                        "id": event.tool_call_id,
                        "type": "function",
                        "function": {
                            "name": event.tool_name,
                            "arguments": event.action.model_dump_json()
                        }
                    }]
                })
        return logs

    @staticmethod
    def logs_to_messages(logs: List[Dict]) -> List[Message]:
        """mcpbench_dev logs → OpenHands Message 格式"""
        messages = []
        for log in logs:
            if log["role"] in ["user", "assistant"]:
                messages.append(Message(
                    role=log["role"],
                    content=[TextContent(text=log["content"])]
                ))
        return messages
```

**7. `utils/openhands_adapter/stats_collector.py`** (新增)
- **功能**: 从 Conversation 收集统计信息
- **行数**: ~100 行

```python
from openhands.sdk.conversation import Conversation
from typing import Dict

class StatsCollector:
    """统计信息收集器"""

    @staticmethod
    def collect_from_conversation(conversation: Conversation) -> Dict:
        """从 Conversation 收集统计信息"""
        stats = conversation.conversation_stats

        return {
            "interaction_turns": len([
                e for e in conversation.state.events
                if isinstance(e, MessageEvent) and e.source == "user"
            ]),
            "tool_calls": len([
                e for e in conversation.state.events
                if isinstance(e, ActionEvent)
            ]),
            "agent_llm_requests": stats.llm_call_count,
            "total_tokens": stats.total_tokens,
            "input_tokens": stats.input_tokens,
            "output_tokens": stats.output_tokens
        }
```

### 4.2 配置文件修改

**8. `utils/data_structures/agent_config.py`**
- **添加**: Condenser 配置字段

```python
@dataclass
class ContextConfig:
    """上下文管理配置"""
    enable_condensation: bool = True
    max_events: int = 120
    keep_first_events: int = 4
    condenser_llm_model: Optional[str] = None  # 用于压缩的 LLM

@dataclass
class AgentConfig:
    # ... 现有字段
    context: ContextConfig = field(default_factory=ContextConfig)
```

**9. `scripts/eval_config.json`**
- **添加**: Condenser 配置

```json
{
  "agent": {
    "context": {
      "enable_condensation": true,
      "max_events": 120,
      "keep_first_events": 4,
      "condenser_llm_model": "gpt-4o-mini"
    }
  }
}
```

### 4.3 工具适配

**10. `utils/aux_tools/*.py` 中的所有工具**
- **需要**: 转换为 OpenHands Tool 格式
- **文件**:
  - `basic.py`
  - `ai_webpage_summary.py`
  - `context_management_tools.py`
  - `history_tools.py`
  - `python_interpretor.py`
  - `web_search.py`

**适配示例** (`utils/aux_tools/web_search.py`):
```python
# === 修改前 (OpenAI SDK 格式) ===
def tool_web_search(query: str) -> str:
    """执行网络搜索"""
    ...

# === 修改后 (OpenHands Tool 格式) ===
from openhands.sdk.tool import Tool, ActionBase, ObservationBase

class WebSearchAction(ActionBase):
    query: str

class WebSearchObservation(ObservationBase):
    result: str

class WebSearchTool(Tool):
    name = "web_search"
    description = "Execute a web search"

    def action_from_arguments(self, arguments: dict) -> WebSearchAction:
        return WebSearchAction(**arguments)

    def __call__(self, action: WebSearchAction) -> WebSearchObservation:
        result = perform_search(action.query)
        return WebSearchObservation(result=result)

# 注册工具
register_tool("WebSearchTool", WebSearchTool)
```

### 4.4 MCP 适配

**11. `utils/mcp/tool_servers.py`**
- **添加**: 格式转换方法
- **行数**: ~50 行新增

```python
class MCPServerManager:
    # ... 现有代码

    def to_openhands_mcp_config(self) -> dict:
        """转换为 OpenHands mcp_config 格式"""
        config = {"mcpServers": {}}

        for name, server in self.servers.items():
            if hasattr(server, 'params'):
                params = server.params
                config["mcpServers"][name] = {
                    "command": params.get("command", ""),
                    "args": params.get("args", []),
                }

                # 处理环境变量
                if "env" in params:
                    config["mcpServers"][name]["env"] = params["env"]

        return config
```

## 五、迁移实施步骤

### 阶段 1: 准备和适配层（1-2天）

**Day 1: 环境准备**
```bash
# 1. 安装 OpenHands SDK 依赖
uv add openhands-sdk

# 2. 创建适配器目录
mkdir -p utils/openhands_adapter

# 3. 创建测试目录
mkdir -p tests/openhands_migration
```

**Day 1-2: 适配层开发**
1. ✅ 创建 `event_converter.py` - 事件格式转换
2. ✅ 创建 `condenser_factory.py` - Condenser 工厂
3. ✅ 创建 `stats_collector.py` - 统计收集
4. ✅ 修改 `MCPServerManager.to_openhands_mcp_config()`
5. ✅ 单元测试各适配器

### 阶段 2: 核心替换（2-3天）

**Day 3: Agent 初始化修改**
1. ✅ 修改 `setup_agent` 方法
2. ✅ 集成 `Condenser`
3. ✅ 创建 `Conversation`
4. ✅ 测试 agent 创建流程

**Day 4: 交互循环重写**
1. ✅ 重写 `run_interaction_loop`
2. ✅ 替换 `ContextManagedRunner.run()` → `Conversation.run()`
3. ✅ 处理用户输入/agent 响应
4. ✅ 测试基本交互

**Day 5: 上下文管理迁移**
1. ✅ 移除手动上下文管理
2. ✅ 配置 `Condenser`
3. ✅ 测试上下文压缩
4. ✅ 验证摘要生成

### 阶段 3: 工具和历史迁移（2天）

**Day 6: 工具适配**
1. ✅ 转换所有本地工具为 OpenHands 格式
2. ✅ 测试工具调用
3. ✅ 验证工具输出

**Day 7: 历史管理适配**
1. ✅ 重构 `ContextManagedRunner` 为工具函数
2. ✅ 实现历史格式转换
3. ✅ 测试检查点恢复

### 阶段 4: 集成测试和优化（2-3天）

**Day 8-9: 端到端测试**
1. ✅ 单任务完整流程测试
2. ✅ 多轮对话测试
3. ✅ 上下文溢出测试
4. ✅ 检查点恢复测试

**Day 10: 性能对比和调优**
1. ✅ 对比迁移前后的性能
2. ✅ 调整 Condenser 参数
3. ✅ 优化统计信息收集

### 阶段 5: 文档和清理（1天）

**Day 11: 文档和清理**
1. ✅ 更新 README
2. ✅ 添加迁移指南
3. ✅ 清理旧代码
4. ✅ 更新配置文件示例

## 六、风险点和缓解策略

### 6.1 高风险点

**1. 上下文连续性问题**
- **风险**: Condenser 摘要可能丢失关键信息
- **缓解**:
  - 调整 `keep_first` 参数保留更多初始事件
  - 使用更强的 LLM (如 GPT-4) 生成摘要
  - 添加关键信息标记机制

**2. 工具调用兼容性**
- **风险**: 工具接口差异导致调用失败
- **缓解**:
  - 创建统一的工具适配层
  - 渐进式迁移（先迁移简单工具）
  - 充分的单元测试

**3. 历史恢复问题**
- **风险**: EventLog 格式与旧 JSONL 不兼容
- **缓解**:
  - 保留旧的历史文件读取逻辑
  - 实现双格式支持
  - 提供迁移脚本

### 6.2 中风险点

**4. 统计信息缺失**
- **风险**: OpenHands stats 可能不包含所有需要的统计
- **缓解**:
  - 通过 event callbacks 补充收集
  - 自定义 ConversationStats 扩展

**5. 性能下降**
- **风险**: EventLog 文件 I/O 可能比内存慢
- **缓解**:
  - 使用 InMemoryFileStore 进行测试
  - 评估是否需要持久化所有事件

### 6.3 低风险点

**6. MCP 集成**
- **风险**: MCP 配置格式转换问题
- **缓解**: 保留原 MCPServerManager，只添加格式转换

**7. 用户模拟器**
- **风险**: 接口变化影响 User 类
- **缓解**: User 类接口基本不变，只需调整获取 agent 响应的方式

## 七、验证清单

### 功能验证
- [ ] Agent 正常创建和初始化
- [ ] 用户消息正常发送
- [ ] Agent 响应正常生成
- [ ] 工具调用正常执行
- [ ] MCP 工具正常可用
- [ ] 上下文自动压缩
- [ ] 摘要正确生成
- [ ] 检查点保存和恢复
- [ ] 多轮对话正常

### 性能验证
- [ ] Token 统计准确
- [ ] Cost 计算正确
- [ ] 响应时间可接受
- [ ] 内存占用合理
- [ ] 文件 I/O 性能

### 兼容性验证
- [ ] 旧配置文件可用
- [ ] 旧任务可以运行
- [ ] 评估系统正常工作
- [ ] 日志格式兼容

## 八、总结

### 核心替换要点

1. **历史管理**: `self.logs` → `conversation.state.events`
2. **上下文传递**: `shared_context` → `ConversationState`
3. **压缩机制**: 手动重置 → `Condenser` 自动压缩
4. **Agent loop**: `ContextManagedRunner.run()` → `Conversation.run()`
5. **工具格式**: OpenAI SDK → OpenHands Tool

### 工作量估算

| 阶段 | 工作量 | 优先级 |
|------|--------|--------|
| 适配层开发 | 1-2 天 | P0 |
| 核心替换 | 2-3 天 | P0 |
| 工具迁移 | 2 天 | P0 |
| 集成测试 | 2-3 天 | P0 |
| 文档清理 | 1 天 | P1 |
| **总计** | **8-11 天** | - |

### 关键优势

✅ **自动压缩**: 无需手动管理上下文重置
✅ **LLM 摘要**: 更自然的历史摘要
✅ **事件驱动**: 更清晰的状态管理
✅ **持久化**: 内置的持久化机制
✅ **线程安全**: FIFOLock 保护
✅ **扩展性**: Microagents 和动态上下文注入

### 潜在挑战

⚠️ **学习曲线**: 团队需要熟悉 OpenHands 架构
⚠️ **调试复杂度**: 事件驱动的调试更复杂
⚠️ **性能不确定**: 文件 I/O 性能需要验证
⚠️ **摘要质量**: 依赖 LLM 摘要的质量
⚠️ **历史兼容**: 需要处理旧格式的历史文件
