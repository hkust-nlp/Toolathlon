# OpenHands SDK 环境替换方案分析

## 一、两个环境的核心差异

### 1.1 mcpbench_dev 环境（当前）

**核心依赖**：基于 OpenAI Agents SDK (agents库)
- 主要组件：`Agent`, `Runner`, `RunConfig`, `Usage`
- Agent loop：使用 `Runner.run()` 方法执行
- 历史管理：自定义 `ContextManagedRunner` 继承自 `Runner`
- MCP管理：自定义 `MCPServerManager` + agents库的 `MCPServerStdio/MCPServerSse`

**Agent Loop 执行流程** (task_agent.py:620-750):
```python
# 1. 用户输入
user_query = await self.user_simulator.interact()
self.logs.append({"role": "user", "content": user_query})

# 2. Agent响应 - 使用 ContextManagedRunner.run()
result = await ContextManagedRunner.run(
    starting_agent=self.agent,
    input=self.logs,  # 完整历史
    context=self.shared_context,
    run_config=RunConfig(model_provider=self.agent_model_provider),
    hooks=self.run_hooks,
    max_turns=remaining_steps,
    history_dir=self.history_dir,
    session_id=self.session_id,
)

# 3. 处理结果
for raw_response in result.raw_responses:
    self.usage.add(raw_response.usage)
self.logs = self.build_new_logs(result.input, result.new_items)

# 4. 传递给用户模拟器
self.user_simulator.receive_message(result.final_output)
```

**特点**：
- 多轮对话由外层 while 循环控制 (task_agent.py:567)
- 每轮可以有多步内部 agent turns (max_inner_turns)
- 支持上下文重置和历史截断
- 自定义历史管理和检查点保存

### 1.2 OpenHands SDK 环境（目标）

**核心依赖**：OpenHands SDK (openhands-sdk)
- 主要组件：`Agent`, `Conversation`, `LLM`, `ConversationState`
- Agent loop：使用 `Conversation.run()` 方法执行
- 历史管理：内置 `ConversationState` + 事件系统
- MCP管理：内置 MCP 客户端 (`openhands.sdk.mcp.client.MCPClient`)

**Agent Loop 执行流程** (conversation.py + agent.py):
```python
# 1. 创建 Conversation
conversation = Conversation(
    agent=agent,
    working_dir=cwd,
    callbacks=[callback_fn],
    max_iteration_per_run=500,
)

# 2. 发送消息
conversation.send_message("User query")

# 3. 运行 agent loop（内部自动循环）
conversation.run()  # 自动运行直到 agent finished

# Agent 内部循环 (agent.py step方法):
# - LLM completion -> tool calls
# - Execute tools -> observations
# - 循环直到没有 tool calls 或达到 max_iteration
```

**特点**：
- Agent loop 完全由 `Conversation.run()` 内部控制
- 基于事件驱动架构 (EventBase, ActionEvent, ObservationEvent)
- 自动管理状态和历史
- 内置 stuck detection 和 visualizer

## 二、需要替换的核心内容

### 2.1 Agent Loop 层面（核心替换）

**当前实现** (task_agent.py:620-750):
```python
# OpenAI Agents SDK 方式
result = await ContextManagedRunner.run(
    starting_agent=self.agent,
    input=self.logs,
    context=self.shared_context,
    run_config=RunConfig(model_provider=self.agent_model_provider),
    max_turns=remaining_steps,
)
```

**需要改为** (OpenHands SDK 方式):
```python
# OpenHands SDK 方式
# 1. 如果是新轮次，发送用户消息
if is_new_user_turn:
    self.conversation.send_message(user_query)

# 2. 运行 agent（内部自动循环）
self.conversation.run()

# 3. 获取最后的 agent 消息
agent_response = self._get_last_agent_message()
```

**关键差异**：
1. **控制粒度**：
   - 当前：外层控制每一步，可以细粒度控制 max_turns
   - 目标：Conversation.run() 内部控制，一次运行到 agent finished

2. **历史管理**：
   - 当前：自己维护 `self.logs` 列表
   - 目标：由 `ConversationState.events` 自动管理

3. **上下文传递**：
   - 当前：通过 `context` 参数传递 shared_context
   - 目标：通过 `ConversationState` 内部管理

### 2.2 Agent 初始化层面

**当前实现** (task_agent.py:416-446):
```python
from agents import Agent, ModelSettings

self.agent = Agent(
    name="Assistant",
    instructions=self.task_config.system_prompts.agent,
    model=self.agent_model_provider.get_model(...),
    mcp_servers=[*self.mcp_manager.get_all_connected_servers()],
    tools=local_tools,
    hooks=self.agent_hooks,
    model_settings=ModelSettings(
        temperature=...,
        top_p=...,
        max_tokens=...,
    ),
)
```

**需要改为**:
```python
from openhands.sdk import Agent, LLM
from openhands.sdk.tool import ToolSpec, register_tool

# 1. 创建 LLM 配置
llm = LLM(
    model=self.agent_config.model.real_name,
    api_key=SecretStr(api_key),
    base_url=base_url,
    temperature=self.agent_config.generation.temperature,
    top_p=self.agent_config.generation.top_p,
    max_tokens=self.agent_config.generation.max_tokens,
)

# 2. 注册工具
for tool_fn in local_tools:
    register_tool(tool_fn.__name__, tool_fn)

# 3. 创建 Agent
self.agent = Agent(
    llm=llm,
    tools=[ToolSpec(name=tool.__name__) for tool in local_tools],
    mcp_config=mcp_config_dict,  # OpenHands 格式的 MCP 配置
)

# 4. 创建 Conversation
self.conversation = Conversation(
    agent=self.agent,
    working_dir=self.task_config.agent_workspace,
    callbacks=[self._event_callback],
    max_iteration_per_run=max_inner_steps,
)
```

### 2.3 MCP 初始化层面（保留原环境）

**决策**：尽量保留 mcpbench_dev 的 MCP 管理方式

**理由**：
1. mcpbench_dev 的 MCPServerManager 已经与任务系统深度集成
2. 支持 task-specific 的 token/key/session 配置
3. 有完善的服务器生命周期管理

**但需要**：
- 将 `MCPServerManager.get_all_connected_servers()` 的返回适配为 OpenHands 所需格式
- 或者在 Agent 初始化时，使用 `mcp_config` 参数代替直接传递 MCP servers

**建议方案**：
```python
# 保留原有的 MCPServerManager 初始化
self.mcp_manager = MCPServerManager(...)
await self.mcp_manager.connect_servers(...)

# 但转换为 OpenHands 的 mcp_config 格式
mcp_config = self._convert_mcp_servers_to_openhands_format()

# 在 Agent 中使用
self.agent = Agent(
    llm=llm,
    tools=tool_specs,
    mcp_config=mcp_config,
)
```

## 三、详细修改清单

### 3.1 task_agent.py 需要修改的部分

#### 修改点 1: 导入语句 (第11-22行)
```python
# 删除
from agents import (
    Agent, RunConfig, Usage, ModelSettings,
    ToolCallItem, ModelProvider, ItemHelpers
)
from agents.exceptions import MaxTurnsExceeded
from utils.roles.context_managed_runner import ContextManagedRunner

# 添加
from openhands.sdk import (
    Agent, LLM, Conversation,
    EventBase, ActionEvent, ObservationEvent, MessageEvent
)
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.tool import ToolSpec, register_tool
from pydantic import SecretStr
```

#### 修改点 2: TaskAgent.__init__ (第83-152行)
```python
# 修改成员变量
self.agent: Optional[Agent] = None
self.conversation: Optional[Conversation] = None  # 新增
self.mcp_manager: Optional[MCPServerManager] = None
self.llm: Optional[LLM] = None  # 新增

# 移除不再需要的
# self.logs: List[Dict] = []  # 由 Conversation 管理
# self.logs_to_record: List[Dict] = []  # 由事件系统管理
# self.usage = Usage()  # 改用 conversation.stats
```

#### 修改点 3: setup_agent (第416-460行)
```python
async def setup_agent(self) -> None:
    """初始化Agent（OpenHands SDK版本）"""

    # 1. 创建 LLM
    self.llm = LLM(
        model=self.agent_config.model.real_name,
        api_key=SecretStr(self._get_api_key()),
        base_url=self._get_base_url(),
        temperature=self.agent_config.generation.temperature,
        top_p=self.agent_config.generation.top_p,
        max_tokens=self.agent_config.generation.max_tokens,
    )

    # 2. 准备本地工具
    local_tools = []
    if self.task_config.needed_local_tools is not None:
        for tool_name in self.task_config.needed_local_tools:
            tool_or_toolsets = local_tool_mappings[tool_name]
            if isinstance(tool_or_toolsets, list):
                local_tools.extend(tool_or_toolsets)
            else:
                local_tools.append(tool_or_toolsets)

    # 3. 注册工具
    tool_specs = []
    for tool in local_tools:
        tool_name = tool.__name__
        register_tool(tool_name, tool)
        tool_specs.append(ToolSpec(name=tool_name))

    # 4. 转换 MCP 配置
    mcp_config = self._convert_mcp_to_openhands_format()

    # 5. 创建 Agent
    self.agent = Agent(
        llm=self.llm,
        tools=tool_specs,
        mcp_config=mcp_config,
        # system_prompt_kwargs 可以传递自定义 prompt
    )

    # 6. 创建 Conversation（但不在这里，在 run_interaction_loop 中）
```

#### 修改点 4: run_interaction_loop (第505-795行) - **最核心的修改**

```python
async def run_interaction_loop(self, abs_original_task_root: str) -> None:
    """运行交互循环（OpenHands SDK 版本）"""

    # 初始化会话
    self.session_id = f"task_{self.task_config.id}_session"
    self.history_dir = os.path.join(abs_original_task_root, "conversation_history")

    # 创建 Conversation
    max_inner_steps = (
        self.agent_config.tool.max_inner_turns
        if not self.single_turn_mode
        else self.task_config.max_steps_under_single_turn_mode
    )

    self.conversation = Conversation(
        agent=self.agent,
        working_dir=self.task_config.agent_workspace,
        persistence_dir=self.history_dir,
        conversation_id=self.session_id,
        callbacks=[self._on_event_callback],
        max_iteration_per_run=max_inner_steps,
        stuck_detection=True,
        visualize=self.debug,
    )

    # 尝试恢复（如果支持）
    if self.allow_resume:
        resumed = await self._load_checkpoint()

    # 主循环
    real_max_turns = 1 if self.single_turn_mode else self.task_config.max_turns

    while self.stats["interaction_turns"] < real_max_turns:
        try:
            # 1. 获取用户输入
            if self.single_turn_mode:
                user_query = self.task_config.task_str
            elif self.manual:
                user_query = await self.ainput("USER: ")
            else:
                user_query = await self.user_simulator.interact()
                self._debug_print(f"USER: {user_query}")

            # 检查用户输入终止条件
            if self.termination_checker(user_query, [], 'user'):
                break

            # 2. 发送消息到 Conversation
            self.conversation.send_message(user_query)

            # 3. 运行 Agent（内部自动循环）
            try:
                self.conversation.run()
            except Exception as e:
                # 处理上下文过长等错误
                if "context" in str(e).lower():
                    await self._handle_context_overflow()
                    continue
                else:
                    raise

            # 4. 获取最后的 agent 响应
            agent_response = self._get_last_agent_message()

            # 5. 传递给用户模拟器
            self.user_simulator.receive_message(agent_response)

            # 6. 更新统计信息
            self.stats["interaction_turns"] += 1
            self._update_stats_from_conversation()

            # 7. 检查终止条件
            if self.termination_checker(agent_response, [], 'agent'):
                break

            # 8. 定期保存检查点
            if self.allow_resume and self.stats["interaction_turns"] % self.checkpoint_interval == 0:
                await self._save_checkpoint()

        except KeyboardInterrupt:
            if self.allow_resume:
                await self._save_checkpoint()
            raise
```

#### 修改点 5: 新增辅助方法

```python
def _on_event_callback(self, event: EventBase) -> None:
    """处理 Conversation 事件的回调"""
    # 记录事件用于统计
    if isinstance(event, ActionEvent):
        self.stats["tool_calls"] += 1
    # 可以添加更多事件处理逻辑

def _get_last_agent_message(self) -> str:
    """从 Conversation 中获取最后一条 agent 消息"""
    state = self.conversation.state
    for event in reversed(state.events):
        if isinstance(event, MessageEvent) and event.source == "agent":
            # 提取文本内容
            message = event.llm_message
            text_parts = [c.text for c in message.content if hasattr(c, 'text')]
            return ' '.join(text_parts)
    return ""

def _update_stats_from_conversation(self) -> None:
    """从 Conversation 更新统计信息"""
    stats = self.conversation.conversation_stats

    # 更新 token 统计
    self.stats["total_tokens"] = stats.total_tokens
    self.stats["input_tokens"] = stats.input_tokens
    self.stats["output_tokens"] = stats.output_tokens
    self.stats["agent_llm_requests"] = stats.llm_call_count

def _convert_mcp_to_openhands_format(self) -> dict:
    """将 mcpbench_dev 的 MCP servers 转换为 OpenHands 格式"""
    # 这需要根据实际的 MCP server 配置来实现
    # OpenHands 期望的格式：
    # {
    #     "mcpServers": {
    #         "server_name": {
    #             "command": "cmd",
    #             "args": ["arg1", "arg2"]
    #         }
    #     }
    # }

    mcp_config = {"mcpServers": {}}

    # 从 MCPServerManager 获取配置
    for server_name, server in self.mcp_manager.servers.items():
        if hasattr(server, 'params'):
            params = server.params
            mcp_config["mcpServers"][server_name] = {
                "command": params.get("command", ""),
                "args": params.get("args", []),
            }

    return mcp_config
```

### 3.2 其他文件的修改

#### utils/general/helper.py
```python
# 修改 build_agent_model_provider
# 原来返回 ModelProvider（OpenAI SDK）
# 需要改为返回适合 OpenHands LLM 的配置

def build_llm_config(agent_config: AgentConfig) -> dict:
    """构建 OpenHands LLM 配置"""
    return {
        "model": agent_config.model.real_name,
        "api_key": os.getenv(agent_config.model.api_key_env),
        "base_url": agent_config.model.base_url,
        "temperature": agent_config.generation.temperature,
        "top_p": agent_config.generation.top_p,
        "max_tokens": agent_config.generation.max_tokens,
    }
```

#### utils/task_runner/runner.py
```python
# TaskRunner.run_single_task 基本不需要改
# 只需要确保传递正确的配置给 TaskAgent
```

### 3.3 保留但需要适配的部分

#### MCPServerManager (utils/mcp/tool_servers.py)
- **保留**：完整的 MCP 服务器管理逻辑
- **适配**：添加方法将配置转换为 OpenHands 格式
```python
def to_openhands_format(self) -> dict:
    """转换为 OpenHands mcp_config 格式"""
    config = {"mcpServers": {}}
    for name, server in self.servers.items():
        config["mcpServers"][name] = {
            "command": server.params.get("command"),
            "args": server.params.get("args", []),
        }
    return config
```

#### ContextManagedRunner
- **移除**：因为 OpenHands Conversation 内置了历史管理
- **但保留**：历史文件的读写逻辑，用于检查点恢复
- **改为**：独立的工具函数，不再继承 Runner

#### 用户模拟器 (utils/roles/user.py)
- **基本保留**：User 类的接口
- **可能需要调整**：如何从 Conversation 获取 agent 响应

## 四、工具和辅助函数的适配

### 4.1 本地工具 (utils/aux_tools/*.py)

OpenHands SDK 期望的工具格式与当前可能不同：

**当前格式** (可能是普通函数):
```python
def tool_web_search(query: str) -> str:
    """Web search tool"""
    ...
```

**OpenHands 期望** (需要符合 Tool 接口):
```python
from openhands.sdk.tool import Tool, ActionBase, ObservationBase

class WebSearchAction(ActionBase):
    query: str

class WebSearchObservation(ObservationBase):
    result: str

class WebSearchTool(Tool):
    name = "web_search"

    def action_from_arguments(self, arguments: dict) -> WebSearchAction:
        return WebSearchAction(**arguments)

    def __call__(self, action: WebSearchAction) -> WebSearchObservation:
        result = perform_search(action.query)
        return WebSearchObservation(result=result)
```

**建议**：
1. 保留现有工具逻辑
2. 创建 OpenHands 格式的包装器
3. 或者写适配层来转换

### 4.2 Hooks 系统

**当前** (utils/task_runner/hooks.py):
```python
class AgentLifecycle:
    def on_agent_created(...): ...

class RunLifecycle:
    def before_run(...): ...
```

**OpenHands**:
使用 callbacks 而不是 hooks：
```python
def event_callback(event: EventBase):
    if isinstance(event, ActionEvent):
        # 处理 action
    elif isinstance(event, ObservationEvent):
        # 处理 observation
```

**适配**：将 hooks 逻辑转换为 event callbacks

## 五、上下文管理和检查点的处理

### 5.1 上下文重置

**当前方案** (task_agent.py:178-235):
- 手动管理 `self.logs`
- 捕获 `ContextTooLongError`
- 手动重置历史

**OpenHands 方案**:
- 使用 `condenser` 自动压缩历史
- 或者手动清空 `conversation.state.events`

**建议实现**:
```python
async def _handle_context_overflow(self):
    """处理上下文溢出"""
    # 方案 1: 使用 condenser（如果配置了）
    # OpenHands Agent 支持配置 condenser

    # 方案 2: 手动清空并保留摘要
    state = self.conversation.state

    # 保存历史摘要
    history_summary = self._get_history_summary(state.events)

    # 清空事件
    state.events.clear()

    # 重新初始化，添加摘要消息
    self.conversation.send_message(
        f"[Context reset] Previous context: {history_summary}\n\n"
        f"Original task: {self.first_user_input}"
    )
```

### 5.2 检查点保存和恢复

**当前方案**:
- 使用 pickle 保存 `self.logs` 等状态
- 手动恢复

**OpenHands 方案**:
- 使用 `persistence_dir` 参数
- Conversation 自动持久化到文件系统

**建议**:
- 利用 OpenHands 的持久化机制
- 额外保存 mcpbench 特定的状态（如统计信息）

## 六、潜在问题和解决方案

### 6.1 控制粒度问题

**问题**: OpenHands 的 `conversation.run()` 一次运行到底，无法像当前那样精细控制每一步

**解决方案**:
1. 使用 `max_iteration_per_run` 限制
2. 使用 `conversation.pause()` 和 resume 机制
3. 自定义 Agent.step() 方法来控制流程

### 6.2 统计信息收集

**问题**: 当前有详细的统计信息收集（turns, tokens, costs等）

**解决方案**:
- 使用 `conversation.conversation_stats` 获取基本统计
- 通过 event callbacks 收集额外信息
- 保留 cost calculation 逻辑

### 6.3 多轮对话管理

**问题**: 当前有明确的外层循环控制多轮对话

**解决方案**:
```python
# 每轮用户输入后都调用 run()
for turn in range(max_turns):
    user_input = get_user_input()
    conversation.send_message(user_input)
    conversation.run()  # 运行直到 agent finished
    # 检查终止条件
```

### 6.4 Single-turn vs Multi-turn 模式

**问题**: 当前明确区分单轮和多轮模式

**解决方案**:
```python
if single_turn_mode:
    # 只允许一次交互
    conversation.send_message(task_str)
    conversation.run()
else:
    # 多轮交互
    while not done:
        conversation.send_message(user_input)
        conversation.run()
```

## 七、迁移步骤建议

### 阶段 1: 准备阶段
1. 安装 OpenHands SDK 依赖
2. 创建工具适配层
3. 编写 MCP 配置转换函数

### 阶段 2: 核心替换
1. 修改 `task_agent.py` 的 `setup_agent` 方法
2. 修改 `run_interaction_loop` 方法
3. 添加必要的辅助方法

### 阶段 3: 功能迁移
1. 迁移统计信息收集
2. 迁移检查点机制
3. 迁移上下文管理

### 阶段 4: 测试和调整
1. 单任务测试
2. 多任务测试
3. 性能对比和优化

## 八、总结

**核心变化**:
1. **Agent loop**: 从手动控制 `Runner.run()` 改为 `Conversation.run()`
2. **历史管理**: 从手动维护 `self.logs` 改为 `ConversationState.events`
3. **工具系统**: 从 OpenAI SDK 工具格式改为 OpenHands Tool 接口
4. **状态管理**: 从手动 context 传递改为 `ConversationState` 自动管理

**保留内容**:
1. MCP服务器管理（`MCPServerManager`）- 只需格式适配
2. 用户模拟器（`User`）- 接口基本不变
3. 任务配置和评估系统 - 完全不变
4. 本地工具的核心逻辑 - 只需接口适配

**关键文件修改优先级**:
1. **高优先级**（核心功能）:
   - `utils/roles/task_agent.py` (主要改动)
   - `utils/general/helper.py` (LLM配置构建)

2. **中优先级**（功能支持）:
   - `utils/aux_tools/*.py` (工具适配)
   - `utils/mcp/tool_servers.py` (MCP格式转换)

3. **低优先级**（优化和增强）:
   - `utils/task_runner/hooks.py` (转换为callbacks)
   - `utils/roles/context_managed_runner.py` (历史管理工具化)

**预期工作量**:
- 核心代码修改: ~500-800 行
- 工具适配层: ~200-400 行
- 测试和调试: 较大工作量
- 总计: 3-5 天开发 + 2-3 天测试
