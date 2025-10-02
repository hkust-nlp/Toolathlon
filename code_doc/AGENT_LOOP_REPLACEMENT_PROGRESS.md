# Agent Loop 完整替换进度

## 当前进度

### ✅ 已完成
1. **LLM 适配器** - 创建了 `utils/openhands_adapter/llm_adapter.py`
2. **导入替换** - 移除 OpenAI Agents SDK，添加 OpenHands SDK 导入

### 🚧 进行中
3. **setup_agent() 替换** - 正在修改

### ⏳ 待完成
4. **run_interaction_loop() 替换**
5. **事件处理替换**
6. **测试和调试**

## 修改说明

由于完整替换涉及 ~500 行代码修改，这里是核心变化摘要：

### setup_agent() 核心变化

**之前（OpenAI Agents SDK）**:
```python
self.agent = Agent(
    name="Assistant",
    instructions=system_prompt,
    model=model,  # OpenAI SDK Model
    mcp_servers=[...],
    tools=local_tools,
    model_settings=ModelSettings(...),
)
```

**之后（OpenHands SDK）**:
```python
# 1. 创建 OpenHands LLM
self.llm = create_openhands_llm_from_config(
    agent_config=self.agent_config,
    agent_model_provider=self.agent_model_provider,
    debug=self.debug,
)

# 2. 创建 Agent
self.agent = OpenHandsAgent(
    llm=self.llm,
    tools=all_tools,  # 本地工具 + MCP 工具
    system_message=self.task_config.system_prompts.agent,
)

# 3. 创建 Conversation
persistence_dir = Path(self.task_config.agent_workspace) / 'conversation_state'
persistence_dir.mkdir(exist_ok=True)

self.conversation = Conversation(
    agent=self.agent,
    working_dir=str(self.task_config.agent_workspace),
    persistence_dir=str(persistence_dir),
    max_iteration_per_run=self.agent_config.tool.max_inner_turns,
    callbacks=[self._on_event],
)
```

### run_interaction_loop() 核心变化

**之前（OpenAI Agents SDK）**:
```python
while turns < max_turns:
    user_input = await get_user_input()
    self.logs.append({"role": "user", "content": user_input})

    result = await ContextManagedRunner.run(
        starting_agent=self.agent,
        input=self.logs,
        context=self.shared_context,
        run_config=RunConfig(...),
        max_turns=remaining_steps,
    )

    await self.process_agent_response(result)
```

**之后（OpenHands SDK）**:
```python
while turns < max_turns:
    user_input = await get_user_input()

    # 发送消息
    self.conversation.send_message(user_input)

    # 记录事件数量
    events_before = len(self.conversation.state.events)

    # 运行 conversation
    self.conversation.run()

    # 提取新事件
    new_events = self.conversation.state.events[events_before:]

    # 处理事件
    await self._process_openhands_events(new_events)

    # 检查状态
    if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
        break
```

## 兼容性处理

### self.all_tools 维护
```python
# 从 Conversation 提取工具定义
available_tools = list(self.agent.tools_map.values())
for tool in available_tools:
    if hasattr(tool, 'to_openai_tool'):
        openai_tool = tool.to_openai_tool()
        self.all_tools.append(openai_tool)
```

### self.logs_to_record 维护
```python
# 从 events 转换为记录格式
for event in events:
    if isinstance(event, MessageEvent):
        if event.source == "user":
            self.logs_to_record.append({
                "role": "user",
                "content": event.content[0].text
            })
        elif event.source == "agent":
            self.logs_to_record.append({
                "role": "assistant",
                "content": event.content[0].text
            })
```

### self.stats 更新
```python
# 从 conversation.state.stats 获取
self.stats["cumulative_tool_calls"] = len([
    e for e in self.conversation.state.events
    if isinstance(e, ActionEvent)
])
```

## 下一步行动

1. 完成 `setup_agent()` 修改
2. 完成 `run_interaction_loop()` 修改
3. 添加 `_process_openhands_events()` 方法
4. 测试基本功能
5. 处理边界情况

---

**状态**: 进行中（第2步/6步）
**估计完成时间**: 由于涉及大量代码，建议分批次实施
