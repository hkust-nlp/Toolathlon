# OpenHands 事件系统完全解析

## 一、什么是事件（Event）？

### 1.1 事件的本质

在 OpenHands SDK 中，**事件（Event）是对话过程中发生的一切行为的记录单元**。它类似于数据库中的事务日志，记录了 agent 与环境交互的完整历史。

**核心理念**：
- 事件是**不可变的**（immutable）- 一旦创建就不能修改
- 事件是**时序的**（temporal）- 按发生顺序排列
- 事件是**可重放的**（replayable）- 通过重放事件可以重建状态

### 1.2 事件 vs 传统消息列表

**传统方式**（如 mcpbench_dev）：
```python
# 简单的字典列表
logs = [
    {"role": "user", "content": "帮我写个程序"},
    {"role": "assistant", "content": "好的", "tool_calls": [...]},
    {"role": "tool", "content": "执行结果..."},
]
```

**OpenHands 事件方式**：
```python
# 类型化的事件对象
events = [
    MessageEvent(
        id="evt-001",
        source="user",
        timestamp="2025-01-15T10:00:00",
        llm_message=Message(role="user", content=[...])
    ),
    ActionEvent(
        id="evt-002",
        source="agent",
        timestamp="2025-01-15T10:00:01",
        thought=[TextContent(text="我需要创建文件")],
        action=WriteFileAction(path="test.py", content="..."),
        tool_name="FileEditorTool",
        tool_call_id="call-123",
        llm_response_id="resp-456"
    ),
    ObservationEvent(
        id="evt-003",
        source="environment",
        timestamp="2025-01-15T10:00:02",
        action_id="evt-002",
        tool_name="FileEditorTool",
        tool_call_id="call-123",
        observation=WriteFileObservation(success=True)
    ),
]
```

**对比优势**：
| 特性 | 传统消息列表 | OpenHands 事件 |
|------|-------------|---------------|
| 类型安全 | ❌ 字典，运行时错误 | ✅ Pydantic 模型，编译时检查 |
| 溯源能力 | ❌ 无法追踪因果关系 | ✅ action_id/tool_call_id 关联 |
| 元数据 | ❌ 需要手动维护 | ✅ 自动包含 id/timestamp/source |
| 可视化 | ❌ 需要自己实现 | ✅ 内置 visualize 方法 |
| 持久化 | ❌ 需要自定义序列化 | ✅ 自动 JSON 序列化 |

## 二、事件类型体系

### 2.1 事件继承结构

```
EventBase (抽象基类)
├── LLMConvertibleEvent (可转换为 LLM 消息)
│   ├── SystemPromptEvent (系统提示)
│   ├── MessageEvent (用户/Agent 消息)
│   ├── ActionEvent (Agent 动作 - 工具调用)
│   ├── ObservationBaseEvent (工具响应基类)
│   │   ├── ObservationEvent (正常工具执行结果)
│   │   ├── UserRejectObservation (用户拒绝)
│   │   └── AgentErrorEvent (Agent 错误)
│   └── CondensationSummaryEvent (压缩摘要)
└── 其他事件
    ├── Condensation (压缩事件)
    ├── CondensationRequest (压缩请求)
    └── PauseEvent (暂停事件)
```

### 2.2 核心事件类型详解

#### (1) EventBase - 所有事件的基类

```python
class EventBase(DiscriminatedUnionMixin, ABC):
    """所有事件的基类"""

    id: EventID = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    source: SourceType  # "user" | "agent" | "environment"

    # 不可变
    model_config = ConfigDict(extra="forbid", frozen=True)
```

**关键字段**：
- `id`: 全局唯一标识符（UUID）
- `timestamp`: 事件发生时间（ISO 格式）
- `source`: 事件来源
  - `"user"`: 用户输入
  - `"agent"`: Agent 生成
  - `"environment"`: 环境/工具响应

#### (2) MessageEvent - 消息事件

```python
class MessageEvent(LLMConvertibleEvent):
    """用户或 Agent 的消息"""

    source: SourceType  # "user" 或 "agent"
    llm_message: Message  # 实际的 LLM 消息

    # 上下文增强
    activated_microagents: list[str] = []  # 激活的 microagent 名称
    extended_content: list[TextContent] = []  # 动态注入的内容

    def to_llm_message(self) -> Message:
        """转换为 LLM 消息"""
        msg = copy.deepcopy(self.llm_message)
        # 合并扩展内容
        msg.content = list(msg.content) + list(self.extended_content)
        return msg
```

**使用场景**：
- 用户发送的消息
- Agent 的纯文本回复（不带工具调用）
- 压缩生成的摘要消息

**示例**：
```python
# 用户消息
user_event = MessageEvent(
    source="user",
    llm_message=Message(
        role="user",
        content=[TextContent(text="帮我创建一个 Python 文件")]
    )
)

# Agent 回复（无工具调用）
agent_event = MessageEvent(
    source="agent",
    llm_message=Message(
        role="assistant",
        content=[TextContent(text="好的，我来帮你创建")]
    )
)
```

#### (3) ActionEvent - 动作事件

```python
class ActionEvent(LLMConvertibleEvent):
    """Agent 调用工具的动作"""

    source: SourceType = "agent"

    # LLM 输出
    thought: Sequence[TextContent]  # Agent 的思考过程
    reasoning_content: str | None  # 推理内容（o1 等推理模型）

    # 工具调用信息
    action: ActionBase  # 具体的动作对象（已验证）
    tool_name: str  # 工具名称
    tool_call_id: ToolCallID  # LLM 返回的工具调用 ID
    tool_call: ChatCompletionMessageToolCall  # 原始工具调用

    # 关联信息
    llm_response_id: EventID  # 同一个 LLM 响应的分组 ID

    # 安全评估
    security_risk: SecurityRisk = SecurityRisk.UNKNOWN

    def to_llm_message(self) -> Message:
        """转换为 LLM 消息"""
        return Message(
            role="assistant",
            content=self.thought,
            tool_calls=[self.tool_call],
            reasoning_content=self.reasoning_content,
        )
```

**关键字段解释**：
- `thought`: Agent 在调用工具前的思考（"我需要创建一个文件..."）
- `action`: 工具调用的具体参数（已经过 Pydantic 验证）
- `tool_call`: 原始的工具调用（保留 LLM 返回的原始格式）
- `llm_response_id`: 用于分组并行工具调用

**并行工具调用示例**：
```python
# LLM 一次返回多个工具调用
response = llm.completion(...)  # 返回 2 个工具调用

# 生成 2 个 ActionEvent，共享同一个 llm_response_id
action1 = ActionEvent(
    id="evt-001",
    llm_response_id="resp-123",  # 相同
    tool_call_id="call-1",
    thought=[TextContent(text="我需要同时...")],  # 只有第一个有 thought
    ...
)

action2 = ActionEvent(
    id="evt-002",
    llm_response_id="resp-123",  # 相同
    tool_call_id="call-2",
    thought=[],  # 后续的 ActionEvent 无 thought
    ...
)
```

#### (4) ObservationEvent - 观察事件

```python
class ObservationEvent(ObservationBaseEvent):
    """工具执行的结果"""

    source: SourceType = "environment"

    # 关联信息
    action_id: EventID  # 对应的 ActionEvent ID
    tool_name: str
    tool_call_id: ToolCallID

    # 执行结果
    observation: ObservationBase  # 工具返回的观察结果

    def to_llm_message(self) -> Message:
        """转换为 LLM 消息"""
        return Message(
            role="tool",
            content=self.observation.agent_observation,
            name=self.tool_name,
            tool_call_id=self.tool_call_id,
        )
```

**示例**：
```python
# 文件创建成功
observation_event = ObservationEvent(
    action_id="evt-002",  # 对应的 ActionEvent ID
    tool_name="FileEditorTool",
    tool_call_id="call-123",
    observation=WriteFileObservation(
        success=True,
        message="File created successfully at test.py"
    )
)
```

#### (5) Condensation - 压缩事件

```python
class Condensation(EventBase):
    """标记历史压缩的特殊事件"""

    source: SourceType = "environment"

    forgotten_event_ids: list[EventID]  # 被遗忘的事件 ID 列表
    summary: str | None  # LLM 生成的摘要
    summary_offset: int | None  # 摘要插入的位置
```

**工作原理**：
1. Condenser 决定删除事件 ID: `["evt-010", "evt-011", ..., "evt-050"]`
2. LLM 生成这些事件的摘要文本
3. 创建 Condensation 事件记录这次压缩
4. 下次构建 View 时，自动过滤掉这些事件，插入摘要

#### (6) CondensationSummaryEvent - 摘要事件

```python
class CondensationSummaryEvent(LLMConvertibleEvent):
    """压缩后生成的摘要（作为 LLM 消息插入）"""

    source: SourceType = "environment"
    summary: str  # 摘要文本

    def to_llm_message(self) -> Message:
        return Message(
            role="user",  # 注意：以 user 角色插入
            content=[TextContent(text=self.summary)],
        )
```

## 三、什么是事件驱动存储？

### 3.1 传统存储 vs 事件驱动存储

**传统存储**（mcpbench_dev）：
```python
# 内存中的列表
self.logs = []

# 添加消息
self.logs.append({"role": "user", "content": "..."})
self.logs.append({"role": "assistant", "content": "..."})

# 保存到文件（全量保存）
with open("history.jsonl", "w") as f:
    for log in self.logs:
        f.write(json.dumps(log) + "\n")

# 问题：
# 1. 内存中完整保存所有历史（占用大）
# 2. 需要手动管理文件写入
# 3. 恢复时需要全量读取
```

**事件驱动存储**（OpenHands）：
```python
# EventLog - 文件支持的列表
class EventLog(ListLike[EventBase]):
    def __init__(self, fs: FileStore, dir_path: str = "events/"):
        self._fs = fs  # 文件系统抽象
        self._dir = dir_path
        self._id_to_idx: dict[EventID, int] = {}  # ID -> 索引映射
        self._idx_to_id: dict[int, EventID] = {}  # 索引 -> ID 映射
        self._length = 0

    def append(self, event: EventBase) -> None:
        """添加事件 - 立即写入文件"""
        # 每个事件一个文件
        path = f"{self._dir}/000042_evt-abc123.json"
        self._fs.write(path, event.model_dump_json())

        # 更新索引
        self._idx_to_id[self._length] = event.id
        self._id_to_idx[event.id] = self._length
        self._length += 1

    def __getitem__(self, idx: int) -> EventBase:
        """按需读取事件"""
        # 从文件读取（不是内存）
        path = self._path(idx)
        txt = self._fs.read(path)
        return EventBase.model_validate_json(txt)

    def __iter__(self):
        """迭代时才加载到内存"""
        for i in range(self._length):
            yield self[i]  # 逐个加载

# 优势：
# 1. 内存占用小（只保存索引，不保存内容）
# 2. 自动持久化（append 时立即写文件）
# 3. 按需加载（访问时才读取）
# 4. 支持大规模历史（几千个事件也不占内存）
```

### 3.2 文件存储结构

```
persistence_dir/
├── base_state.json          # 对话状态快照
│   {
│       "id": "conv-123",
│       "agent": {...},
│       "working_dir": "/path/to/workspace",
│       "max_iterations": 500,
│       "agent_status": "idle"
│   }
│
└── events/                  # 事件目录
    ├── 000000_evt-uuid1.json   # 第 0 个事件
    │   {
    │       "kind": "MessageEvent",
    │       "id": "evt-uuid1",
    │       "source": "user",
    │       "timestamp": "2025-01-15T10:00:00",
    │       "llm_message": {...}
    │   }
    │
    ├── 000001_evt-uuid2.json   # 第 1 个事件
    │   {
    │       "kind": "ActionEvent",
    │       "id": "evt-uuid2",
    │       "source": "agent",
    │       "thought": [...],
    │       "action": {...}
    │   }
    │
    └── 000002_evt-uuid3.json   # 第 2 个事件
        {
            "kind": "ObservationEvent",
            "id": "evt-uuid3",
            "source": "environment",
            "action_id": "evt-uuid2",
            "observation": {...}
        }
```

**文件命名规则**：`{索引:06d}_{事件ID}.json`
- `000000`: 6 位数字索引（方便排序）
- `evt-uuid1`: 事件的唯一 ID

### 3.3 EventLog 的核心操作

#### 写入事件
```python
state = ConversationState.create(...)
state.events  # 返回 EventLog 实例

# 添加事件（自动写入文件）
event = MessageEvent(source="user", ...)
state.events.append(event)

# 底层执行：
# 1. 生成文件名: "events/000000_evt-abc123.json"
# 2. 序列化: event.model_dump_json()
# 3. 写入文件: fs.write(path, json)
# 4. 更新索引: _idx_to_id[0] = "evt-abc123"
```

#### 读取事件
```python
# 按索引访问（懒加载）
event = state.events[0]  # 从文件读取
event = state.events[42]  # 从文件读取

# 切片访问
recent = state.events[-10:]  # 读取最后 10 个事件

# 迭代访问
for event in state.events:  # 逐个从文件加载
    print(event)

# 按 ID 查找
idx = state.events.get_index("evt-abc123")
event = state.events[idx]
```

#### 恢复会话
```python
# 首次创建
state1 = ConversationState.create(
    id="conv-123",
    agent=agent,
    persistence_dir="/path/to/persist"
)
state1.events.append(event1)
state1.events.append(event2)

# 程序重启后恢复
state2 = ConversationState.create(
    id="conv-123",  # 相同的 ID
    agent=agent,
    persistence_dir="/path/to/persist"  # 相同的目录
)

# 自动恢复：
# 1. 读取 base_state.json
# 2. 扫描 events/ 目录，重建索引
# 3. state2.events 包含所有历史事件（但不在内存中）

print(len(state2.events))  # 2（从索引得知，未加载到内存）
print(state2.events[0])    # 从文件加载第一个事件
```

## 四、Agent Loop 中的事件流

### 4.1 完整的事件流程图

```
用户输入 "创建 test.py 文件"
    ↓
┌─────────────────────────────────────────────────────────┐
│ 1. Conversation.send_message()                          │
│    创建 MessageEvent(source="user", ...)                │
│    ↓                                                     │
│    调用 on_event(message_event)                         │
│    ↓                                                     │
│    state.events.append(message_event)  ← 写入文件       │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Conversation.run() - 启动循环                        │
│    while not finished:                                  │
│        agent.step(state, on_event)                      │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Agent.step() - 单步执行                              │
│                                                          │
│    (a) 检查是否需要压缩                                  │
│        if condenser:                                    │
│            view = View.from_events(state.events)        │
│            result = condenser.condense(view)            │
│            if isinstance(result, Condensation):         │
│                on_event(condensation) ← 写入文件         │
│                return  # 不执行 LLM，等下一轮            │
│                                                          │
│    (b) 构建 LLM 消息                                     │
│        messages = LLMConvertibleEvent.events_to_messages│
│                   (llm_convertible_events)              │
│                                                          │
│    (c) 调用 LLM                                          │
│        response = llm.completion(messages, tools)       │
│                                                          │
│    (d) 解析工具调用，创建 ActionEvent                    │
│        for tool_call in response.tool_calls:            │
│            action_event = ActionEvent(...)              │
│            on_event(action_event)  ← 写入文件            │
│                                                          │
│    (e) 执行工具                                          │
│        for action_event in action_events:               │
│            observation = tool.execute(action_event)     │
│            obs_event = ObservationEvent(               │
│                action_id=action_event.id,               │
│                observation=observation                  │
│            )                                             │
│            on_event(obs_event)  ← 写入文件               │
└─────────────────────────────────────────────────────────┘
    ↓
    重复 Agent.step() 直到：
    - Agent 返回纯文本消息（无工具调用）
    - 达到 max_iteration_per_run
    - 用户请求暂停
```

### 4.2 详细代码流程

#### 步骤 1: 用户发送消息

```python
# examples/01_hello_world.py
conversation.send_message("创建一个 Python 文件")

# ↓ 内部实现 (conversation/impl/local_conversation.py:137)
def send_message(self, message: str | Message) -> None:
    # 转换为 Message 对象
    if isinstance(message, str):
        message = Message(role="user", content=[TextContent(text=message)])

    # 检查 microagents（动态上下文注入）
    activated_microagents = []
    extended_content = []
    if self.agent.agent_context:
        ctx = self.agent.agent_context.get_user_message_suffix(
            user_message=message,
            skip_microagent_names=self._state.activated_knowledge_microagents
        )
        if ctx:
            content, activated_microagents = ctx
            extended_content.append(content)

    # 创建 MessageEvent
    user_msg_event = MessageEvent(
        source="user",
        llm_message=message,
        activated_microagents=activated_microagents,
        extended_content=extended_content,
    )

    # 触发回调 → 写入 EventLog
    self._on_event(user_msg_event)

    # ↓ _on_event 实现 (local_conversation.py:83-84)
    def _default_callback(e):
        self._state.events.append(e)  # ← 这里写入文件

    # ↓ EventLog.append (event_store.py:76-89)
    def append(self, item: EventBase) -> None:
        evt_id = item.id

        # 生成文件路径
        path = f"{self._dir}/{self._length:06d}_{evt_id}.json"

        # 写入文件
        self._fs.write(path, item.model_dump_json(exclude_none=True))

        # 更新索引
        self._idx_to_id[self._length] = evt_id
        self._id_to_idx[evt_id] = self._length
        self._length += 1
```

**文件系统变化**：
```
events/
└── 000000_evt-user-msg-1.json  ← 新增
    {
        "kind": "MessageEvent",
        "id": "evt-user-msg-1",
        "source": "user",
        "timestamp": "2025-01-15T10:00:00.123",
        "llm_message": {
            "role": "user",
            "content": [{"type": "text", "text": "创建一个 Python 文件"}]
        },
        "activated_microagents": [],
        "extended_content": []
    }
```

#### 步骤 2: 启动对话循环

```python
conversation.run()

# ↓ 内部实现 (local_conversation.py:190-254)
def run(self) -> None:
    iteration = 0
    while True:
        with self._state:  # 获取状态锁
            # 检查终止条件
            if self._state.agent_status in [
                AgentExecutionStatus.FINISHED,
                AgentExecutionStatus.PAUSED,
                AgentExecutionStatus.STUCK,
            ]:
                break

            # 检查是否卡住
            if self._stuck_detector:
                if self._stuck_detector.is_stuck():
                    self._state.agent_status = AgentExecutionStatus.STUCK
                    continue

            # 执行一步
            self.agent.step(self._state, on_event=self._on_event)
            iteration += 1

            # 检查是否达到最大迭代次数
            if iteration >= self.max_iteration_per_run:
                break
```

#### 步骤 3: Agent 单步执行

```python
# agent/agent.py:129-258
def step(self, state: ConversationState, on_event):
    # === 3.1 检查是否有待确认的动作 ===
    pending_actions = ConversationState.get_unmatched_actions(state.events)
    if pending_actions:
        # 确认模式：执行待确认的动作
        self._execute_actions(state, pending_actions, on_event)
        return

    # === 3.2 检查是否需要压缩 ===
    if self.condenser is not None:
        view = View.from_events(state.events)
        condensation_result = self.condenser.condense(view)

        match condensation_result:
            case View():
                llm_convertible_events = condensation_result.events

            case Condensation():
                # 需要压缩 - 添加 Condensation 事件
                on_event(condensation_result)
                return  # 不执行 LLM，下一轮再试
    else:
        llm_convertible_events = [
            e for e in state.events if isinstance(e, LLMConvertibleEvent)
        ]

    # === 3.3 构建 LLM 消息 ===
    _messages = LLMConvertibleEvent.events_to_messages(llm_convertible_events)

    # === 3.4 调用 LLM ===
    try:
        llm_response = self.llm.completion(
            messages=_messages,
            tools=list(self.tools_map.values()),
        )
    except Exception as e:
        # 处理上下文窗口超出
        if (self.condenser is not None and
            self.condenser.handles_condensation_requests() and
            self.llm.is_context_window_exceeded_exception(e)):

            # 触发压缩请求
            on_event(CondensationRequest())
            return
        else:
            raise e

    message: Message = llm_response.message

    # === 3.5 处理 LLM 响应 ===
    if message.tool_calls and len(message.tool_calls) > 0:
        # 有工具调用
        action_events: list[ActionEvent] = []

        for i, tool_call in enumerate(message.tool_calls):
            action_event = self._get_action_event(
                state, tool_call,
                llm_response_id=llm_response.id,
                on_event=on_event,
                thought=thought_content if i == 0 else [],
                reasoning_content=message.reasoning_content if i == 0 else None,
            )
            if action_event:
                action_events.append(action_event)

        # 检查是否需要用户确认
        if self._requires_user_confirmation(state, action_events):
            return

        # 执行工具
        if action_events:
            self._execute_actions(state, action_events, on_event)
    else:
        # 无工具调用 - Agent 完成
        state.agent_status = AgentExecutionStatus.FINISHED
        msg_event = MessageEvent(
            source="agent",
            llm_message=message,
        )
        on_event(msg_event)
```

#### 步骤 3.5.1: 创建 ActionEvent

```python
# agent/agent.py:299-376
def _get_action_event(
    self, state, tool_call, llm_response_id, on_event,
    thought=[], reasoning_content=None
) -> ActionEvent | None:

    tool_name = tool_call.function.name
    tool = self.tools_map.get(tool_name)

    # 工具不存在 - 创建错误事件
    if tool is None:
        err = f"Tool '{tool_name}' not found. Available: {list(self.tools_map.keys())}"
        event = AgentErrorEvent(
            error=err,
            tool_name=tool_name,
            tool_call_id=tool_call.id,
        )
        on_event(event)  # ← 写入文件
        return None

    # 验证参数
    try:
        arguments = json.loads(tool_call.function.arguments)
        action: ActionBase = tool.action_from_arguments(arguments)
    except (json.JSONDecodeError, ValidationError) as e:
        err = f"Error validating args for '{tool.name}': {e}"
        event = AgentErrorEvent(
            error=err,
            tool_name=tool_name,
            tool_call_id=tool_call.id,
        )
        on_event(event)  # ← 写入文件
        return None

    # 创建 ActionEvent
    action_event = ActionEvent(
        action=action,
        thought=thought,
        reasoning_content=reasoning_content,
        tool_name=tool.name,
        tool_call_id=tool_call.id,
        tool_call=tool_call,
        llm_response_id=llm_response_id,
    )

    on_event(action_event)  # ← 写入文件
    return action_event
```

**文件系统变化**：
```
events/
├── 000000_evt-user-msg-1.json
└── 000001_evt-action-1.json  ← 新增
    {
        "kind": "ActionEvent",
        "id": "evt-action-1",
        "source": "agent",
        "timestamp": "2025-01-15T10:00:01.456",
        "thought": [
            {"type": "text", "text": "我需要创建一个文件"}
        ],
        "action": {
            "kind": "WriteFileAction",
            "path": "test.py",
            "content": "print('hello')"
        },
        "tool_name": "FileEditorTool",
        "tool_call_id": "call-xyz789",
        "tool_call": {...},
        "llm_response_id": "resp-abc123"
    }
```

#### 步骤 3.5.2: 执行工具并创建 ObservationEvent

```python
# agent/agent.py:378-413
def _execute_action_event(
    self, state, action_event, on_event
):
    tool = self.tools_map.get(action_event.tool_name)

    # 执行工具
    observation: ObservationBase = tool(action_event.action)

    # 创建 ObservationEvent
    obs_event = ObservationEvent(
        observation=observation,
        action_id=action_event.id,
        tool_name=tool.name,
        tool_call_id=action_event.tool_call.id,
    )

    on_event(obs_event)  # ← 写入文件

    # 检查是否是 finish 工具
    if tool.name == FinishTool.name:
        state.agent_status = AgentExecutionStatus.FINISHED

    return obs_event
```

**文件系统变化**：
```
events/
├── 000000_evt-user-msg-1.json
├── 000001_evt-action-1.json
└── 000002_evt-obs-1.json  ← 新增
    {
        "kind": "ObservationEvent",
        "id": "evt-obs-1",
        "source": "environment",
        "timestamp": "2025-01-15T10:00:02.789",
        "action_id": "evt-action-1",
        "tool_name": "FileEditorTool",
        "tool_call_id": "call-xyz789",
        "observation": {
            "kind": "WriteFileObservation",
            "success": true,
            "message": "File created: test.py"
        }
    }
```

### 4.3 压缩事件的流程

当事件数量超过 `max_size` 时：

```python
# 假设当前有 150 个事件，max_size=120, keep_first=4

# 1. Agent.step() 开始
if self.condenser is not None:
    view = View.from_events(state.events)  # 150 个事件

    # 2. Condenser 检查
    if len(view) > self.max_size:  # 150 > 120
        # 3. 执行压缩
        condensation = self.condenser.get_condensation(view)

        # 4. 计算要遗忘的事件
        head = view[:4]  # 前 4 个
        target_size = 120 // 2 = 60
        events_from_tail = 60 - 4 - 1 = 55
        forgotten_events = view[4:-55]  # 中间 91 个事件

        # 5. LLM 生成摘要
        prompt = f"总结以下事件：\n{forgotten_events}"
        summary = llm.completion(prompt)

        # 6. 创建 Condensation 事件
        condensation = Condensation(
            forgotten_event_ids=[e.id for e in forgotten_events],  # 91 个 ID
            summary=summary,
            summary_offset=4,  # 在第 4 个位置插入
        )

        # 7. 写入 Condensation 事件
        on_event(condensation)
        return  # 不执行 LLM
```

**文件系统变化**：
```
events/
├── ... (150 个事件文件，都保留)
└── 000150_evt-condensation-1.json  ← 新增
    {
        "kind": "Condensation",
        "id": "evt-condensation-1",
        "source": "environment",
        "timestamp": "2025-01-15T10:05:00",
        "forgotten_event_ids": [
            "evt-004", "evt-005", ..., "evt-094"  // 91 个 ID
        ],
        "summary": "在之前的交互中，用户请求创建了多个文件...",
        "summary_offset": 4
    }
```

**下一轮 Agent.step() 时**：

```python
# View.from_events() 处理压缩
view = View.from_events(state.events)  # 151 个事件

# 内部逻辑：
forgotten_event_ids = set()
for event in events:
    if isinstance(event, Condensation):
        # 收集所有被遗忘的 ID
        forgotten_event_ids.update(event.forgotten_event_ids)
        forgotten_event_ids.add(event.id)  # 也忘记 Condensation 本身

# 过滤事件
kept_events = [
    e for e in events
    if e.id not in forgotten_event_ids and isinstance(e, LLMConvertibleEvent)
]
# kept_events 现在只有: 前4个 + 后55个 = 59 个事件

# 插入摘要
summary_event = CondensationSummaryEvent(
    summary="在之前的交互中..."
)
kept_events.insert(4, summary_event)  # 在第 4 个位置插入

# 最终 View: 60 个事件（4 + 1摘要 + 55）
```

## 五、事件系统的核心优势

### 5.1 可追溯性（Traceability）

**传统方式**：
```python
logs = [
    {"role": "user", "content": "创建文件"},
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool", "content": "成功"},
]
# 问题：无法知道第 3 条消息对应哪个工具调用
```

**事件方式**：
```python
events = [
    MessageEvent(id="evt-1", ...),
    ActionEvent(id="evt-2", tool_call_id="call-1", ...),
    ObservationEvent(id="evt-3", action_id="evt-2", tool_call_id="call-1", ...),
]
# 可以通过 action_id 和 tool_call_id 精确追踪因果关系
```

### 5.2 时间溯源（Temporal Ordering）

每个事件都有精确的时间戳：
```python
event.timestamp  # "2025-01-15T10:00:01.123456"
```

可以：
- 重放历史（按时间顺序重新执行）
- 性能分析（计算每步耗时）
- 审计追踪（谁在什么时候做了什么）

### 5.3 按需加载（Lazy Loading）

```python
# 传统方式 - 全量加载
logs = load_all_history()  # 10000 条消息，占用大量内存

# 事件方式 - 按需加载
state.events  # 只保存索引，不加载内容
last_10 = state.events[-10:]  # 只加载最后 10 个事件
```

### 5.4 类型安全（Type Safety）

```python
# 传统方式 - 运行时错误
log = {"role": "user", "conent": "..."}  # 拼写错误，运行时才发现
content = log["content"]  # KeyError

# 事件方式 - 编译时检查
event = MessageEvent(
    source="user",
    conent="..."  # Pydantic 立即报错
)
```

### 5.5 扩展性（Extensibility）

添加新功能只需添加新事件类型：
```python
class CodeExecutionEvent(LLMConvertibleEvent):
    """代码执行事件"""
    code: str
    language: str
    execution_result: str

    def to_llm_message(self) -> Message:
        return Message(
            role="user",
            content=[TextContent(text=f"执行结果：{self.execution_result}")]
        )
```

## 六、与 mcpbench_dev 的对接方案

### 6.1 事件 → Logs 转换

```python
class EventToLogsConverter:
    """将 OpenHands 事件转换为 mcpbench_dev logs 格式"""

    @staticmethod
    def convert(events: List[EventBase]) -> List[Dict]:
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

            elif isinstance(event, ObservationEvent):
                logs.append({
                    "role": "tool",
                    "tool_call_id": event.tool_call_id,
                    "name": event.tool_name,
                    "content": extract_observation(event.observation)
                })

        return logs
```

### 6.2 统计信息收集

```python
class EventStatsCollector:
    """从事件流收集统计信息"""

    @staticmethod
    def collect(events: List[EventBase]) -> Dict:
        stats = {
            "interaction_turns": 0,
            "tool_calls": 0,
            "errors": 0,
            "condensations": 0,
        }

        for event in events:
            if isinstance(event, MessageEvent) and event.source == "user":
                stats["interaction_turns"] += 1
            elif isinstance(event, ActionEvent):
                stats["tool_calls"] += 1
            elif isinstance(event, AgentErrorEvent):
                stats["errors"] += 1
            elif isinstance(event, Condensation):
                stats["condensations"] += 1

        return stats
```

## 七、总结

### 事件系统的本质

1. **事件（Event）** = 对话过程中的原子记录单元
2. **事件驱动存储** = 每个事件立即持久化到独立文件
3. **EventLog** = 文件支持的列表，按需加载，自动索引
4. **View** = 事件到 LLM 消息的动态视图，支持压缩

### 核心流程

```
用户消息 → MessageEvent → 写入文件
    ↓
Agent.step()
    ↓
检查压缩 → (可选) Condensation → 写入文件
    ↓
View.from_events() → 过滤+插入摘要
    ↓
LLM completion
    ↓
ActionEvent → 写入文件
    ↓
执行工具
    ↓
ObservationEvent → 写入文件
    ↓
循环直到完成
```

### 关键优势

✅ **不可变性** - 事件创建后不可修改，保证历史真实性
✅ **可追溯性** - 通过 ID 关联，精确追踪因果关系
✅ **按需加载** - 只保存索引，访问时才读取，节省内存
✅ **自动持久化** - append 时立即写文件，无需手动保存
✅ **类型安全** - Pydantic 模型，编译时检查
✅ **易于扩展** - 添加新事件类型即可扩展功能

这就是 OpenHands 事件系统的完整解析！
