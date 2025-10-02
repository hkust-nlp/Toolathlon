# Agent Loop 替换方案：从 OpenAI Agents SDK 到 OpenHands SDK

## 当前问题

**错误**: `Hosted tools are not supported with the ChatCompletions API`

**根本原因**:
- 当前使用 **OpenAI Agents SDK** (`from agents import Agent, Runner`)
- OpenHands 的 `MCPTool` 对象无法直接被 OpenAI Agents SDK 使用
- 两个 SDK 有完全不同的架构和 API

## 架构对比

### 当前架构（OpenAI Agents SDK）
```python
# task_agent.py
from agents import Agent, RunConfig
from utils.roles.context_managed_runner import ContextManagedRunner

# 创建 Agent
self.agent = Agent(
    name="Assistant",
    instructions=system_prompt,
    model=model,
    mcp_servers=[...],  # OpenAI SDK 的 MCP 服务器
    tools=local_tools,
)

# 运行 loop
while turns < max_turns:
    user_input = await get_user_input()
    self.logs.append({"role": "user", "content": user_input})

    # 使用 ContextManagedRunner (自定义的 Runner 包装)
    result = await ContextManagedRunner.run(
        starting_agent=self.agent,
        input=self.logs,  # List[Dict]
        context=self.shared_context,  # 手动管理的上下文
        run_config=RunConfig(...),
        max_turns=remaining_steps,
    )

    # 手动处理结果和工具调用
    await self.process_agent_response(result)
```

### 目标架构（OpenHands SDK）
```python
# task_agent.py
from openhands.sdk.agent.agent import Agent
from openhands.sdk.conversation import Conversation

# 创建 Agent
self.openhands_agent = Agent(
    llm=llm,
    tools=all_tools,  # 包含 OpenHands MCPTool
    system_message=system_prompt,
)

# 创建 Conversation
self.conversation = Conversation(
    agent=self.openhands_agent,
    working_dir=workspace,
    persistence_dir=event_store_dir,
    max_iteration_per_run=max_iterations,
)

# 运行 loop
while turns < max_turns:
    user_input = await get_user_input()

    # 发送消息
    self.conversation.send_message(user_input)

    # 运行直到完成
    self.conversation.run()

    # 检查状态和事件
    if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
        break
```

## 迁移策略

### 阶段 1: 创建 OpenHands Agent 和 Conversation

1. **修改 `setup_agent()`**:
   - 创建 OpenHands Agent 而不是 OpenAI Agents
   - 创建 Conversation 对象
   - 配置 working_dir 和 persistence_dir

2. **创建 LLM 适配器**:
   - OpenHands SDK 需要 LLM 对象（不是 Model）
   - 创建适配器将 `self.agent_model_provider` 转换为 OpenHands LLM

### 阶段 2: 替换 run_interaction_loop()

1. **简化循环逻辑**:
   - 移除 `ContextManagedRunner`
   - 移除手动的 `self.logs` 管理
   - 移除 `self.shared_context` 管理

2. **使用 OpenHands Conversation**:
   - 使用 `conversation.send_message()` 发送用户消息
   - 使用 `conversation.run()` 执行 agent 步骤
   - 使用 `conversation.state.events` 访问事件历史

3. **事件处理**:
   - 注册 callback 处理事件
   - 从事件中提取工具调用和响应信息

### 阶段 3: 兼容性处理

1. **保持现有接口**:
   - `self.all_tools` - 仍然维护（用于 User simulator）
   - `self.stats` - 从 Conversation.state.stats 获取
   - `self.logs_to_record` - 从 events 转换

2. **上下文管理**:
   - OpenHands 使用 Condenser 自动管理上下文
   - 移除手动的上下文截断逻辑
   - 配置 Condenser 参数

## 详细实现计划

### 文件修改清单

| 文件 | 修改内容 | 估计行数 |
|------|---------|---------|
| `task_agent.py` | 替换 Agent 和 loop | ~300 行修改 |
| `llm_adapter.py` (新建) | LLM 适配器 | ~150 行新增 |

### 代码示例

#### 新的 setup_agent()
```python
async def setup_agent(self) -> None:
    """初始化 OpenHands Agent 和 Conversation"""

    # 1. 创建 LLM
    from utils.openhands_adapter.llm_adapter import create_openhands_llm

    self.openhands_llm = create_openhands_llm(
        model_provider=self.agent_model_provider,
        model_name=self.agent_config.model.real_name,
        temperature=self.agent_config.generation.temperature,
        max_tokens=self.agent_config.generation.max_tokens,
    )

    # 2. 收集工具
    local_tools = [...]  # 本地工具
    all_tools = local_tools + self.mcp_tools

    # 3. 创建 OpenHands Agent
    from openhands.sdk.agent.agent import Agent

    self.openhands_agent = Agent(
        llm=self.openhands_llm,
        tools=all_tools,
        system_message=self.task_config.system_prompts.agent,
    )

    # 4. 创建 Conversation
    from openhands.sdk.conversation import Conversation

    persistence_dir = self.task_config.agent_workspace / 'conversation_state'
    persistence_dir.mkdir(exist_ok=True)

    self.conversation = Conversation(
        agent=self.openhands_agent,
        working_dir=str(self.task_config.agent_workspace),
        persistence_dir=str(persistence_dir),
        max_iteration_per_run=self.agent_config.tool.max_inner_turns,
        callbacks=[self._on_event_callback],
    )

    # 5. 维护兼容性
    await self._populate_all_tools_from_conversation()
```

#### 新的 run_interaction_loop()
```python
async def run_interaction_loop(self, abs_original_task_root: str) -> None:
    """运行交互循环（使用 OpenHands Conversation）"""

    if self.debug:
        print_color("=== Starting interaction loop (OpenHands) ===", "blue")

    max_turns = 1 if self.single_turn_mode else self.task_config.max_turns

    while self.stats["interaction_turns"] < max_turns:
        try:
            # 获取用户输入
            if self.single_turn_mode:
                user_query = self.task_config.task_str
            elif self.manual:
                user_query = await self.ainput("USER: ")
            else:
                user_query = await self.user_simulator.interact()
                self._debug_print(f"USER: {user_query}")

            # 保存第一轮用户输入
            if self.first_user_input is None:
                self.first_user_input = user_query

            # 发送消息到 Conversation
            self.conversation.send_message(user_query)

            # 记录事件数量（用于后续提取新事件）
            events_before = len(self.conversation.state.events)

            # 运行 Conversation（直到 agent 完成或达到 max_iteration）
            self.conversation.run()

            # 提取新事件
            new_events = self.conversation.state.events[events_before:]

            # 处理事件
            await self._process_events(new_events)

            # 增加交互轮次
            self.stats["interaction_turns"] += 1

            # 检查终止条件
            if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
                self._debug_print("Agent finished the task")
                break

            if self.termination_checker(user_query, [], 'user'):
                self._debug_print("Termination condition met by user input")
                break

        except Exception as e:
            print_color(f"Error in interaction loop: {e}", "red")
            if self.debug:
                import traceback
                traceback.print_exc()
            break
```

#### 事件处理
```python
async def _process_events(self, events: List[Event]) -> None:
    """处理新事件，提取信息用于记录和终止检查"""
    for event in events:
        if isinstance(event, MessageEvent):
            # Agent 消息
            if event.source == "agent":
                self.logs_to_record.append({
                    "role": "assistant",
                    "content": event.content[0].text if event.content else ""
                })

        elif isinstance(event, ActionEvent):
            # 工具调用
            self.stats["cumulative_tool_calls"] += 1

        elif isinstance(event, ObservationEvent):
            # 工具结果
            pass
```

## 迁移风险和缓解

### 风险 1: User Simulator 兼容性
**问题**: User simulator 依赖 `self.all_tools` 格式
**缓解**: 维护 `self.all_tools` 列表，从 Conversation 的工具转换

### 风险 2: 历史记录格式变化
**问题**: 当前使用 `self.logs` 和 JSONL 文件
**缓解**: 从 OpenHands events 转换为兼容格式

### 风险 3: 上下文管理差异
**问题**: 原有的手动截断逻辑
**缓解**: 使用 OpenHands Condenser，配置合适参数

## 预期收益

1. ✅ 解决 "Hosted tools not supported" 错误
2. ✅ 使用 OpenHands 的 Event 系统（更强大的历史管理）
3. ✅ 自动化上下文管理（Condenser）
4. ✅ 支持 OpenHands MCP 工具
5. ✅ 更现代的架构

## 工作量估算

- 创建 LLM 适配器: **2-3 小时**
- 修改 setup_agent: **2-3 小时**
- 替换 run_interaction_loop: **4-6 小时**
- 测试和调试: **4-6 小时**
- **总计: 12-18 小时 (1.5-2 天)**

## 下一步

1. 创建 LLM 适配器
2. 修改 setup_agent 创建 OpenHands Agent
3. 替换 run_interaction_loop 使用 Conversation
4. 测试基本功能
5. 处理兼容性问题
6. 完整测试
