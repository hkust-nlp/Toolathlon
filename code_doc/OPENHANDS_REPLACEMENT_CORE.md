# OpenHands Agent Loop 替换 - 核心修改记录

## 已完成修改 ✅

### 1. 导入替换（第1-64行）
- 移除：`from agents import Agent, RunConfig, ...`
- 添加：`from openhands.sdk.agent.agent import Agent as OpenHandsAgent`
- 添加：`from openhands.sdk.conversation import Conversation`
- 添加：`from utils.openhands_adapter import create_openhands_llm_from_config`

### 2. setup_agent() 替换（第494-582行）
```python
async def setup_agent(self) -> None:
    # 1. 创建 OpenHands LLM
    self.llm = create_openhands_llm_from_config(...)

    # 2. 收集工具
    all_tools = local_tools + self.mcp_tools

    # 3. 创建 OpenHands Agent
    self.agent = OpenHandsAgent(
        llm=self.llm,
        tools=all_tools,
        system_message=system_prompt,
    )

    # 4. 创建 Conversation
    self.conversation = Conversation(
        agent=self.agent,
        working_dir=workspace,
        persistence_dir=persistence_dir,
        max_iteration_per_run=max_inner_turns,
        callbacks=[self._on_event],
    )

    # 5. 维护 self.all_tools
    for tool in self.agent.tools_map.values():
        openai_tool = tool.to_openai_tool()
        self.all_tools.append(openai_tool)
```

### 3. _on_event() 回调（第584-616行）
```python
def _on_event(self, event) -> None:
    # 处理 MessageEvent
    if isinstance(event, MessageEvent):
        if event.source == "agent":
            self.logs_to_record.append({
                "role": "assistant",
                "content": event.content[0].text
            })

    # 处理 ActionEvent
    elif isinstance(event, ActionEvent):
        self.stats["cumulative_tool_calls"] += 1
```

## 待完成修改 ⏳

### 4. run_interaction_loop() 替换（~第661行）

**核心逻辑**：
```python
async def run_interaction_loop(self, abs_original_task_root: str) -> None:
    # 简化初始化（移除 self.logs, self.shared_context）
    self.session_id = f"task_{self.task_config.id}_session"

    max_turns = 1 if self.single_turn_mode else self.task_config.max_turns

    while self.stats["interaction_turns"] < max_turns:
        # 1. 获取用户输入
        if self.single_turn_mode:
            user_query = self.task_config.task_str
        elif self.manual:
            user_query = await self.ainput("USER: ")
        else:
            user_query = await self.user_simulator.interact()

        # 保存第一轮输入
        if self.first_user_input is None:
            self.first_user_input = user_query

        # 记录用户消息
        self.logs_to_record.append({"role": "user", "content": user_query})

        # 2. 发送消息到 Conversation
        self.conversation.send_message(user_query)

        # 3. 运行 Conversation
        self.conversation.run()

        # 4. 增加交互轮次
        self.stats["interaction_turns"] += 1

        # 5. 检查终止条件
        if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
            break

        if self.termination_checker(user_query, [], 'user'):
            break

        # 单轮模式只执行一次
        if self.single_turn_mode:
            break
```

### 5. 移除的方法
- `process_agent_response()` - 不再需要（事件在 _on_event 处理）
- `_reset_context_and_history()` - OpenHands 自动管理上下文
- `_check_context_overflow()` - 使用 Condenser 替代

## 关键变化总结

| 组件 | 之前 | 之后 |
|------|------|------|
| Agent | `agents.Agent` | `OpenHandsAgent` |
| Loop | `ContextManagedRunner.run()` | `Conversation.run()` |
| 历史 | `self.logs` (List[Dict]) | `conversation.state.events` |
| 上下文 | 手动管理 `shared_context` | Condenser 自动管理 |
| 事件 | 手动处理 result.new_items | 回调 `_on_event()` |

## 下一步行动

1. ✅ 完成 setup_agent() 修改
2. ⏳ 完成 run_interaction_loop() 修改
3. ⏳ 移除不再需要的方法
4. ⏳ 测试基本功能

## 文件位置
- `/ssddata/mcpbench/wenshuo/scaffold/mcpbench_dev/utils/roles/task_agent.py`
- LLM 适配器: `utils/openhands_adapter/llm_adapter.py`

## 重要提示
- **不使用 adapter 兼容 OpenAI SDK**
- **完全替换为 OpenHands SDK**
- **移除所有 OpenAI Agents SDK 依赖**
