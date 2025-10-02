# MCP Server 管理机制深度对比：mcpbench_dev vs OpenHands SDK

## 一、核心架构对比

### 1.1 整体设计哲学

| 方面 | mcpbench_dev | OpenHands SDK |
|------|--------------|---------------|
| **设计理念** | 显式管理、完全控制 | 隐式集成、自动化 |
| **配置方式** | YAML 文件 + 模板变量 | 内联 Dict |
| **生命周期管理** | 手动 connect/disconnect | 自动 context manager |
| **服务器存储** | 预加载所有配置 | 按需创建 |
| **工具列表** | 主动管理连接状态 | 一次性获取 |
| **重试机制** | 内置多层重试 | 简单超时 |

### 1.2 架构图对比

**mcpbench_dev 架构**：
```
┌─────────────────────────────────────────────────────────────┐
│                    MCPServerManager                          │
├─────────────────────────────────────────────────────────────┤
│  初始化阶段：                                                 │
│  1. _load_servers_from_configs(config_dir)                  │
│     ├─ 扫描 configs/mcp_servers/*.yaml                      │
│     ├─ 解析每个 YAML 文件                                    │
│     ├─ 处理模板变量 ${agent_workspace}, ${token.*}          │
│     └─ 创建 MCPServerStdio/MCPServerSse 实例                │
│        (存储在 self.servers 字典中，未连接)                  │
│                                                              │
│  连接阶段：                                                   │
│  2. connect_servers(server_names)                           │
│     ├─ 对每个 server 创建异步任务                            │
│     ├─ _manage_server_lifecycle(name, server)               │
│     │   ├─ 重试连接 (max_connect_retries=3)                 │
│     │   ├─ async with server: (调用 __aenter__)             │
│     │   ├─ 验证连接：await server.list_tools()              │
│     │   ├─ 保持连接：await asyncio.sleep(inf)               │
│     │   └─ 清理：__aexit__                                  │
│     └─ 等待所有连接完成 (asyncio.Event)                      │
│                                                              │
│  工具调用阶段：                                               │
│  3. call_tool_with_retry(server, tool_name, args)          │
│     └─ 重试 5 次，间隔 1 秒                                  │
│                                                              │
│  断开阶段：                                                   │
│  4. disconnect_servers(server_names)                        │
│     ├─ task.cancel() 取消所有任务                           │
│     ├─ 等待清理完成 (重试 3 次)                              │
│     └─ 强制清理状态                                          │
└─────────────────────────────────────────────────────────────┘

状态管理：
  self.servers = {"filesystem": MCPServerStdio(...), ...}  # 所有配置
  self.connected_servers = {"filesystem": server}  # 已连接
  self._server_tasks = {"filesystem": Task}  # 运行中的任务
  self._connection_events = {"filesystem": Event}  # 连接事件
```

**OpenHands SDK 架构**：
```
┌─────────────────────────────────────────────────────────────┐
│                    create_mcp_tools(config)                  │
├─────────────────────────────────────────────────────────────┤
│  一次性流程（在 Agent 初始化时执行）：                        │
│                                                              │
│  1. 解析 mcp_config 字典                                     │
│     config = {                                               │
│       "mcpServers": {                                        │
│         "fetch": {                                           │
│           "command": "uvx",                                  │
│           "args": ["mcp-server-fetch"]                       │
│         }                                                    │
│       }                                                      │
│     }                                                        │
│     ↓                                                        │
│  2. MCPConfig.model_validate(config)                        │
│     - Pydantic 验证配置格式                                  │
│     ↓                                                        │
│  3. MCPClient(config)                                        │
│     - 基于 fastmcp.Client                                    │
│     - 拥有独立的事件循环 (AsyncExecutor)                     │
│     ↓                                                        │
│  4. client.call_async_from_sync(_list_tools, timeout=30)   │
│     ├─ async with client:  (连接)                           │
│     ├─ client.list_tools()  (获取工具列表)                  │
│     ├─ 对每个工具创建 MCPTool 实例                           │
│     └─ __aexit__ (断开连接)                                 │
│     ↓                                                        │
│  5. 返回 List[MCPTool]                                       │
│     - 每个 MCPTool 包含：                                    │
│       - mcp_tool: mcp.types.Tool (工具定义)                 │
│       - executor: MCPToolExecutor(tool_name, client)        │
│       - client: MCPClient (独立客户端)                       │
│                                                              │
│  工具调用阶段（每次调用工具时）：                             │
│  6. tool(action)                                             │
│     └─ executor.call_tool(action)                           │
│        └─ async with client:  (重新连接)                    │
│           └─ client.call_tool_mcp(name, args)               │
│              └─ __aexit__ (断开连接)                        │
└─────────────────────────────────────────────────────────────┘

特点：
  - 无状态管理（每次调用重新连接）
  - 工具列表一次性获取
  - 每个工具调用都是独立的 context manager
```

## 二、初始化和配置详细对比

### 2.1 mcpbench_dev：YAML 配置 + 模板系统

#### 配置文件结构

**文件位置**：`configs/mcp_servers/*.yaml`

**示例 1：文件系统服务器** (`filesystem.yaml`)
```yaml
# 基础配置
type: stdio                  # 服务器类型：stdio 或 sse
name: filesystem            # 服务器名称（唯一标识）

# 启动参数
params:
  command: npx              # 启动命令
  args:                     # 命令参数
    - "-y"
    - "@modelcontextprotocol/server-filesystem"
    - "${agent_workspace}"  # 模板变量：动态替换

# 可选配置
client_session_timeout_seconds: 300  # 超时时间
cache_tools_list: true               # 缓存工具列表
```

**示例 2：Playwright 浏览器** (`playwright_with_chunk.yaml`)
```yaml
type: stdio
name: playwright_with_chunk
params:
  command: npx
  args:
    - "-y"
    - "@lockon0927/playwright-mcp-with-chunk"
    - "--headless"
    - "--isolated"
    - "--browser"
    - "chromium"
    - "--user-agent"
    - "Mozilla/5.0 ..."
    - "--output-dir"
    - "${agent_workspace}/.playwright_output"  # 模板变量
    - "--image-responses"
    - "omit"
    - "--span-size"
    - "5000"
client_session_timeout_seconds: 120
cache_tools_list: true
```

**示例 3：Arxiv 服务器** (`arxiv_local.yaml`)
```yaml
type: stdio
name: arxiv_local
params:
  command: uv
  args:
    - "run"
    - "arxiv-mcp-server"
    - "--storage-path"
    - "${agent_workspace}/arxiv_local_storage"  # 模板变量
  # 环境变量支持
  env:
    HTTPS_PROXY: "${config.proxy}"  # 从全局配置读取
    HTTP_PROXY: "${config.proxy}"
client_session_timeout_seconds: 60
cache_tools_list: true
```

#### 模板变量系统

**定义位置**：`MCPServerManager._get_template_variables()`

**可用变量类型**：

1. **基础路径变量**
```python
{
    'agent_workspace': '/path/to/task/workspace',
    'local_servers_paths': '/path/to/local_servers',
    'local_binary_paths': '/path/to/local_binary',
    'podman_or_docker': 'docker',
}
```

2. **全局配置变量** (来自 `configs/global_configs`)
```python
# 自动添加所有 global_configs 属性
{
    'config.proxy': 'http://proxy:7890',
    'config.podman_or_docker': 'docker',
    'config.some_setting': 'value',
    # ... 所有配置项
}
```

3. **Token/Key/Session 变量** (来自 `configs/token_key_session.py`)
```python
# 全局 token
{
    'token.github_token': 'ghp_xxx',
    'token.notion_token': 'secret_xxx',
    'token.openai_api_key': 'sk-xxx',
    # ... 所有 token
}

# Task-specific token（优先级更高）
# 从 tasks/{task_name}/token_key_session.py 读取
{
    'token.github_token': 'task_specific_token',  # 覆盖全局
}
```

**模板替换逻辑** (`_process_config_params`)：
```python
def _process_config_params(self, params: Dict) -> Dict:
    template_vars = self._get_template_variables()

    def replace_templates(obj):
        if isinstance(obj, str):
            # 正则替换 ${var_name}
            pattern = r'\$\{([^}]+)\}'
            return re.sub(pattern, lambda m: template_vars.get(m.group(1), m.group(0)), obj)
        elif isinstance(obj, list):
            return [replace_templates(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: replace_templates(v) for k, v in obj.items()}
        return obj

    return replace_templates(params)
```

**替换示例**：
```yaml
# YAML 配置
args:
  - "--output-dir"
  - "${agent_workspace}/.playwright_output"
  - "--token"
  - "${token.github_token}"

# 替换后
args:
  - "--output-dir"
  - "/tasks/task001/workspace/.playwright_output"
  - "--token"
  - "ghp_abc123xyz"
```

#### 初始化流程

**步骤 1：扫描 YAML 文件**
```python
# MCPServerManager.__init__
def _load_servers_from_configs(self, config_dir: str):
    config_path = Path(config_dir)

    # 遍历所有 .yaml 文件
    for config_file in config_path.glob("*.yaml"):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            self._initialize_server_from_config(config, config_file.stem)
```

**步骤 2：解析单个配置**
```python
def _initialize_server_from_config(self, config: Dict, default_name: str):
    server_type = config.get('type', 'stdio')  # stdio 或 sse
    server_name = config.get('name', default_name)

    # 处理模板变量
    params = self._process_config_params(config.get('params', {}))

    # 特殊处理（如 playwright 的 root 用户检测）
    if server_name == 'playwright_with_chunk':
        if os.geteuid() == 0:  # root 用户
            params['args'].append('--no-sandbox')

    # 创建服务器实例（未连接）
    if server_type == 'stdio':
        server = MCPServerStdio(
            name=server_name,
            params=params,
            cache_tools_list=config.get('cache_tools_list', True),
            client_session_timeout_seconds=config.get('client_session_timeout_seconds')
        )
    elif server_type == 'sse':
        server = MCPServerSse(...)

    # 存储（未连接状态）
    self.servers[server_name] = server
```

**初始化后状态**：
```python
manager.servers = {
    'filesystem': MCPServerStdio(name='filesystem', params={...}),
    'playwright_with_chunk': MCPServerStdio(name='playwright_with_chunk', params={...}),
    'github': MCPServerStdio(name='github', params={...}),
    # ... 35+ 个服务器配置
}

manager.connected_servers = {}  # 空，尚未连接
```

### 2.2 OpenHands SDK：内联配置 + 自动创建

#### 配置格式

**定义位置**：Agent 初始化时传入

**格式**：简单的嵌套字典
```python
mcp_config = {
    "mcpServers": {
        "server_name": {
            "command": "command_to_run",
            "args": ["arg1", "arg2"],
            # 可选
            "env": {"VAR": "value"},
            "url": "http://...",  # SSE 服务器
            "auth": "oauth",       # OAuth 认证
        }
    }
}
```

**示例 1：Stdio 服务器**
```python
mcp_config = {
    "mcpServers": {
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()]
        }
    }
}
```

**示例 2：SSE 服务器 + OAuth**
```python
mcp_config = {
    "mcpServers": {
        "Notion": {
            "url": "https://mcp.notion.com/mcp",
            "auth": "oauth"
        }
    }
}
```

**示例 3：混合配置**
```python
mcp_config = {
    "mcpServers": {
        "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
        "repomix": {"command": "npx", "args": ["-y", "repomix@1.4.2", "--mcp"]},
        "notion": {"url": "https://mcp.notion.com/mcp", "auth": "oauth"},
    }
}
```

#### 初始化流程

**步骤 1：Agent 初始化时调用**
```python
# agent/base.py:199-205
def model_post_init(self, __context) -> None:
    # ... 其他初始化

    # 创建 MCP 工具
    if self.mcp_config:
        mcp_tools = create_mcp_tools(self.mcp_config, timeout=30)
        for tool in mcp_tools:
            self._tools[tool.name] = tool
```

**步骤 2：create_mcp_tools 实现**
```python
# mcp/utils.py:49-61
def create_mcp_tools(config: dict | MCPConfig, timeout: float = 30.0) -> list[MCPTool]:
    # 1. 验证配置格式
    if isinstance(config, dict):
        config = MCPConfig.model_validate(config)  # Pydantic 验证

    # 2. 创建客户端
    client = MCPClient(config, log_handler=log_handler)

    # 3. 同步调用异步函数（在独立事件循环中）
    tools = client.call_async_from_sync(_list_tools, timeout=timeout, client=client)

    logger.info(f"Created {len(tools)} MCP tools: {[t.name for t in tools]}")
    return tools
```

**步骤 3：_list_tools 实现**
```python
# mcp/utils.py:33-46
async def _list_tools(client: MCPClient) -> list[ToolBase]:
    tools: list[ToolBase] = []

    # 连接并获取工具列表
    async with client:  # __aenter__: 连接服务器
        assert client.is_connected()

        # 获取 MCP 工具定义
        mcp_type_tools: list[mcp.types.Tool] = await client.list_tools()

        # 为每个工具创建 MCPTool
        for mcp_tool in mcp_type_tools:
            tool_sequence = MCPTool.create(mcp_tool=mcp_tool, mcp_client=client)
            tools.extend(tool_sequence)
    # __aexit__: 断开连接

    return tools
```

**步骤 4：MCPTool.create 实现**
```python
# mcp/tool.py:147-183
@classmethod
def create(cls, mcp_tool: mcp.types.Tool, mcp_client: MCPClient) -> Sequence["MCPTool"]:
    # 动态创建 Action 类型（从 MCP schema）
    mcp_action_type = _create_mcp_action_type(mcp_tool)

    return [
        cls(
            name=mcp_tool.name,
            description=mcp_tool.description or "No description",
            action_type=MCPToolAction,  # 通用 action wrapper
            observation_type=MCPToolObservation,
            executor=MCPToolExecutor(
                tool_name=mcp_tool.name,
                client=mcp_client  # 每个工具保存 client 引用
            ),
            mcp_tool=mcp_tool,  # 保存原始定义
        )
    ]
```

**初始化后状态**：
```python
agent._tools = {
    'fetch': MCPTool(
        name='fetch',
        executor=MCPToolExecutor(tool_name='fetch', client=client1)
    ),
    'repomix_pack_codebase': MCPTool(
        name='repomix_pack_codebase',
        executor=MCPToolExecutor(tool_name='repomix_pack_codebase', client=client2)
    ),
    # ... 所有工具
}

# 注意：此时所有 MCP 服务器已经断开连接
# 每次调用工具时会重新连接
```

## 三、服务器生命周期管理对比

### 3.1 mcpbench_dev：持久连接模式

#### 连接流程

**显式连接**：
```python
# task_agent.py:906
await self.setup_mcp_servers(self.task_config.local_token_key_session)

# ↓
# tool_servers.py:233-278
async def connect_servers(self, server_names: List[str]):
    async with self._lock:
        tasks_to_wait = []

        for name in server_names:
            server = self.servers[name]

            # 创建连接事件
            event = asyncio.Event()
            self._connection_events[name] = event

            # 创建生命周期管理任务
            task = asyncio.create_task(
                self._manage_server_lifecycle(name, server),
                name=f"mcp_server_{name}"
            )
            self._server_tasks[name] = task
            tasks_to_wait.append((name, event))

        # 等待所有服务器连接完成
        await asyncio.gather(*[event.wait() for name, event in tasks_to_wait])

        # 验证连接数量
        connected_count = sum(1 for name, _ in tasks_to_wait if name in self.connected_servers)
        print(f"Successfully connected {connected_count}/{len(tasks_to_wait)} servers")
```

#### 生命周期管理

**_manage_server_lifecycle 详解**：
```python
# tool_servers.py:163-231
async def _manage_server_lifecycle(
    self, name: str, server: MCPServerStdio,
    max_connect_retries: int = 3,
    connect_retry_delay: float = 2.0
):
    event = self._connection_events.get(name)

    # === 连接阶段（带重试） ===
    for connect_attempt in range(max_connect_retries + 1):
        try:
            # 使用 context manager 连接
            async with server:  # __aenter__: 连接服务器
                # 连接成功 - 添加到已连接列表
                self.connected_servers[name] = server

                # 通知连接完成
                if event:
                    event.set()

                # 验证连接（可选）
                if self.debug:
                    tools = await server.list_tools()
                    print(f"Server {name} has {len(tools)} tools")

                # === 保持连接阶段 ===
                # 无限等待，直到任务被取消
                try:
                    await asyncio.sleep(float('inf'))
                except asyncio.CancelledError:
                    # 正常取消 - 触发 __aexit__
                    print(f"Disconnecting server {name}")
                    raise

            # 连接成功，跳出重试循环
            break

        except asyncio.CancelledError:
            # 预期的取消，重新抛出
            raise
        except Exception as e:
            # 连接失败，重试
            if connect_attempt < max_connect_retries:
                print(f"Connection failed (attempt {connect_attempt + 1}), retrying...")
                await asyncio.sleep(connect_retry_delay)
            else:
                print(f"Connection failed after {max_connect_retries + 1} attempts")
                if event:
                    event.set()  # 避免死等

    # === 清理阶段 ===
    try:
        self.connected_servers.pop(name, None)
        self._server_tasks.pop(name, None)
        self._connection_events.pop(name, None)
    except Exception as e:
        print(f"Cleanup error: {e}")
```

**连接状态图**：
```
[初始状态]
  ↓
[创建任务] → task = asyncio.create_task(_manage_server_lifecycle)
  ↓
[尝试连接] → async with server:
  ↓ (成功)
[已连接] → self.connected_servers[name] = server
  ↓
[设置事件] → event.set()  (通知主线程)
  ↓
[保持连接] → await asyncio.sleep(inf)
  ↓ (收到 CancelledError)
[断开连接] → __aexit__ 自动调用
  ↓
[清理状态] → pop from all dicts
  ↓
[完成]
```

#### 断开流程

**显式断开**：
```python
# task_agent.py:878
await self.cleanup()

# ↓
# tool_servers.py:280-367
async def disconnect_servers(self, server_names: List[str]):
    async with self._lock:
        # 1. 取消所有任务
        tasks_to_cancel = []
        for name in servers_to_disconnect:
            if task := self._server_tasks.get(name):
                task.cancel()  # 发送 CancelledError
                tasks_to_cancel.append((name, task))

        # 2. 立即从已连接列表移除（防止并发调用）
        for name in servers_to_disconnect:
            self.connected_servers.pop(name, None)

        # 3. 等待任务完成清理（带重试）
        for disconnect_attempt in range(max_disconnect_retries + 1):
            try:
                # 等待所有任务完成（10秒超时）
                await asyncio.wait_for(
                    asyncio.gather(*[task for name, task in tasks_to_cancel], return_exceptions=True),
                    timeout=10.0
                )

                # 检查是否所有任务都完成
                still_running = [name for name, task in tasks_to_cancel if not task.done()]
                if not still_running:
                    break  # 全部完成
                else:
                    # 还有未完成的，重试
                    if disconnect_attempt < max_disconnect_retries:
                        await asyncio.sleep(disconnect_retry_delay)
                    else:
                        # 强制取消
                        for name in still_running:
                            if task := self._server_tasks.get(name):
                                task.cancel()

            except asyncio.TimeoutError:
                # 超时，重试
                if disconnect_attempt < max_disconnect_retries:
                    await asyncio.sleep(disconnect_retry_delay)
```

#### 工具调用

**调用已连接的服务器**：
```python
# 在 Agent 内部
server = mcp_manager.connected_servers['filesystem']

# 直接调用（带重试）
result = await call_tool_with_retry(
    server=server,
    tool_name="read_file",
    arguments={"path": "test.txt"},
    retry_time=5,
    delay=1.0
)
```

**call_tool_with_retry 实现**：
```python
# tool_servers.py:450-483
async def call_tool_with_retry(
    server, tool_name: str, arguments: dict,
    retry_time: int = 5, delay: float = 1.0
):
    last_exception = None

    for attempt in range(retry_time + 1):
        try:
            # 服务器已连接，直接调用
            result = await server.call_tool(tool_name=tool_name, arguments=arguments)
            return result
        except Exception as e:
            last_exception = e
            if attempt < retry_time:
                print(f"Tool call failed (attempt {attempt + 1}), retrying...")
                await asyncio.sleep(delay)
            else:
                print(f"Tool call failed after {retry_time + 1} attempts")

    raise ToolCallError(f"Tool call failed: {tool_name}", last_exception)
```

**优点**：
- ✅ 连接一次，多次使用（性能好）
- ✅ 连接状态可查询
- ✅ 支持长时间运行的任务
- ✅ 多层重试机制（连接重试 + 调用重试）

**缺点**：
- ❌ 需要手动管理连接生命周期
- ❌ 需要处理连接断开/重连
- ❌ 复杂的状态管理（4个字典）

### 3.2 OpenHands SDK：按需连接模式

#### 工具调用流程

**每次调用都重新连接**：
```python
# 用户代码
agent._tools['fetch'](action)

# ↓
# mcp/tool.py:110-130 - MCPTool.__call__
def __call__(self, action: ActionBase) -> ObservationBase:
    # 验证 action 类型
    if not isinstance(action, MCPToolAction):
        raise ValueError(f"Expected MCPToolAction, got {type(action)}")

    # 动态验证参数
    mcp_action_type = _create_mcp_action_type(self.mcp_tool)
    mcp_action_type.model_validate(action.data)

    # 调用 executor（同步接口）
    return super().__call__(action)

# ↓
# tool/tool.py - Tool.__call__
def __call__(self, action: ActionBase) -> ObservationBase:
    return self.executor(action)

# ↓
# mcp/tool.py:68-72 - MCPToolExecutor.__call__
def __call__(self, action: MCPToolAction) -> MCPToolObservation:
    # 同步调用异步方法（在独立事件循环中）
    return self.client.call_async_from_sync(
        self.call_tool,
        action=action,
        timeout=300  # 5分钟超时
    )

# ↓
# mcp/tool.py:45-66 - MCPToolExecutor.call_tool
async def call_tool(self, action: MCPToolAction) -> MCPToolObservation:
    # === 每次调用都重新连接 ===
    async with self.client:  # __aenter__: 连接
        assert self.client.is_connected()

        try:
            # 调用 MCP 工具
            result: mcp.types.CallToolResult = await self.client.call_tool_mcp(
                name=self.tool_name,
                arguments=action.to_mcp_arguments()
            )

            # 转换结果
            return MCPToolObservation.from_call_tool_result(
                tool_name=self.tool_name,
                result=result
            )
        except Exception as e:
            # 错误处理
            return MCPToolObservation(
                content=[TextContent(text=f"Error: {e}")],
                is_error=True,
                tool_name=self.tool_name
            )
    # __aexit__: 断开连接
```

**调用时序图**：
```
[开始]
  ↓
[Tool.__call__] → tool(action)
  ↓
[Executor.__call__] → executor(action)
  ↓
[call_async_from_sync] → 在独立事件循环中运行异步代码
  ↓
[async with client] → __aenter__: 连接服务器
  ↓
[client.call_tool_mcp] → 调用 MCP 工具
  ↓
[返回结果]
  ↓
[__aexit__] → 断开连接
  ↓
[返回 Observation]
  ↓
[完成]
```

#### MCPClient 实现

**基于 fastmcp + 独立事件循环**：
```python
# mcp/client.py:13-74
class MCPClient(AsyncMCPClient):  # 继承 fastmcp.Client
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 创建独立的事件循环执行器
        self._executor = AsyncExecutor()

    def call_async_from_sync(
        self, awaitable_or_fn, *args, timeout: float, **kwargs
    ) -> Any:
        """从同步代码调用异步函数"""
        return self._executor.run_async(
            awaitable_or_fn, *args, timeout=timeout, **kwargs
        )

    def sync_close(self) -> None:
        """同步关闭客户端"""
        # 尝试异步关闭
        if hasattr(self, "close") and inspect.iscoroutinefunction(self.close):
            try:
                self._executor.run_async(self.close, timeout=10.0)
            except Exception:
                pass

        # 清理执行器
        self._executor.close()

    def __del__(self):
        """析构时清理"""
        try:
            self.sync_close()
        except Exception:
            pass
```

**优点**：
- ✅ 无需管理连接状态（自动）
- ✅ 无资源泄漏（自动清理）
- ✅ 实现简单（基于 context manager）
- ✅ 每次调用都是干净的连接

**缺点**：
- ❌ 每次调用都重新连接（性能开销）
- ❌ 无法查询连接状态
- ❌ 不适合高频调用
- ❌ 无内置重试机制

## 四、配置灵活性对比

### 4.1 mcpbench_dev：强大的模板系统

#### 支持的配置场景

**场景 1：动态工作目录**
```yaml
# filesystem.yaml
params:
  command: npx
  args:
    - "@modelcontextprotocol/server-filesystem"
    - "${agent_workspace}"  # 每个任务不同
```

**场景 2：任务特定的 Token**
```yaml
# github.yaml
params:
  command: npx
  args:
    - "@modelcontextprotocol/server-github"
  env:
    GITHUB_TOKEN: "${token.github_token}"  # 每个任务可以不同
```

**场景 3：全局配置（代理）**
```yaml
# arxiv_local.yaml
params:
  env:
    HTTPS_PROXY: "${config.proxy}"
    HTTP_PROXY: "${config.proxy}"
```

**场景 4：条件配置（运行时决定）**
```python
# 特殊处理逻辑
if server_name == 'playwright_with_chunk':
    if os.geteuid() == 0:  # root 用户
        params['args'].append('--no-sandbox')
```

**场景 5：本地服务器路径**
```yaml
# custom_server.yaml
params:
  command: python
  args:
    - "${local_servers_paths}/my_server/main.py"
    - "--workspace"
    - "${agent_workspace}"
```

#### 配置优先级

```
1. Task-specific token (tasks/{task}/token_key_session.py)
   ↓ (覆盖)
2. Global token (configs/token_key_session.py)
   ↓
3. Global config (configs/global_configs.py)
   ↓
4. Built-in defaults
```

**示例**：
```python
# 全局 token
all_token_key_session = {
    'github_token': 'global_token_123',
    'notion_token': 'global_notion_abc',
}

# Task 001 的 token（tasks/task001/token_key_session.py）
local_token_key_session = {
    'github_token': 'task001_specific_token',  # 覆盖全局
    # notion_token 使用全局值
}

# 最终模板变量
{
    'token.github_token': 'task001_specific_token',  # Task-specific
    'token.notion_token': 'global_notion_abc',       # Global
}
```

### 4.2 OpenHands SDK：简单的内联配置

#### 支持的配置场景

**场景 1：基本 Stdio 服务器**
```python
mcp_config = {
    "mcpServers": {
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        }
    }
}
```

**场景 2：SSE 服务器**
```python
mcp_config = {
    "mcpServers": {
        "notion": {
            "url": "https://mcp.notion.com/mcp",
            "auth": "oauth"
        }
    }
}
```

**场景 3：环境变量**
```python
mcp_config = {
    "mcpServers": {
        "github": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN")  # 手动读取
            }
        }
    }
}
```

**场景 4：动态构建**
```python
# 在代码中动态构建
working_dir = os.getcwd()

mcp_config = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                working_dir  # Python 变量
            ]
        }
    }
}
```

#### 限制

- ❌ 无模板系统（需要手动构建）
- ❌ 无配置文件分离（硬编码在代码中）
- ❌ 无 task-specific 配置支持
- ❌ 无配置优先级系统
- ✅ 简单直接
- ✅ 适合简单场景

## 五、工具过滤机制

### 5.1 mcpbench_dev：按需选择服务器

**按服务器名称选择**：
```python
# 在 task_config.json 中指定
{
    "needed_mcp_servers": ["filesystem", "github", "playwright_with_chunk"]
}

# 只连接这 3 个服务器
await mcp_manager.connect_servers(task_config.needed_mcp_servers)
```

**所有工具都可用**（连接后）：
```python
# 连接后，该服务器的所有工具都可用
server = mcp_manager.connected_servers['filesystem']
tools = await server.list_tools()
# ['read_file', 'write_file', 'list_directory', 'move_file', ...]
```

### 5.2 OpenHands SDK：Regex 过滤

**按工具名称过滤**：
```python
mcp_config = {
    "mcpServers": {
        "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
        "repomix": {"command": "npx", "args": ["-y", "repomix@1.4.2", "--mcp"]},
    }
}

# 过滤掉除了 pack_codebase 之外的所有 repomix 工具
agent = Agent(
    llm=llm,
    tools=tool_specs,
    mcp_config=mcp_config,
    filter_tools_regex="^(?!repomix)(.*)|^repomix.*pack_codebase.*$",
    #                   ^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^
    #                   保留非 repomix     只保留 repomix_pack_codebase
)
```

**过滤逻辑** (agent/base.py):
```python
def model_post_init(self, __context) -> None:
    # 创建所有工具
    all_tools = []
    all_tools.extend(local_tools)
    all_tools.extend(mcp_tools)

    # 应用过滤
    if self.filter_tools_regex:
        pattern = re.compile(self.filter_tools_regex)
        all_tools = [t for t in all_tools if pattern.match(t.name)]

    # 存储
    for tool in all_tools:
        self._tools[tool.name] = tool
```

## 六、错误处理和重试机制

### 6.1 mcpbench_dev：多层重试

**连接重试**：
```python
# _manage_server_lifecycle
for connect_attempt in range(max_connect_retries + 1):  # 默认 3 次
    try:
        async with server:
            # 连接成功
            break
    except Exception as e:
        if connect_attempt < max_connect_retries:
            await asyncio.sleep(connect_retry_delay)  # 默认 2 秒
```

**调用重试**：
```python
# call_tool_with_retry
for attempt in range(retry_time + 1):  # 默认 5 次
    try:
        result = await server.call_tool(tool_name, arguments)
        return result
    except Exception as e:
        if attempt < retry_time:
            await asyncio.sleep(delay)  # 默认 1 秒
```

**断开重试**：
```python
# disconnect_servers
for disconnect_attempt in range(max_disconnect_retries + 1):  # 默认 3 次
    try:
        await asyncio.wait_for(asyncio.gather(...), timeout=10.0)
        break
    except asyncio.TimeoutError:
        if disconnect_attempt < max_disconnect_retries:
            await asyncio.sleep(disconnect_retry_delay)  # 默认 1 秒
```

**重试统计**：
- 连接重试：3 次，间隔 2 秒
- 调用重试：5 次，间隔 1 秒
- 断开重试：3 次，间隔 1 秒
- **总重试次数：11 次**

### 6.2 OpenHands SDK：简单超时

**只有超时机制**：
```python
# create_mcp_tools
tools = client.call_async_from_sync(
    _list_tools,
    timeout=30.0  # 30 秒超时
)

# call_tool
return self.client.call_async_from_sync(
    self.call_tool,
    action=action,
    timeout=300  # 5 分钟超时
)
```

**无自动重试**：
- ❌ 连接失败 → 直接抛出异常
- ❌ 调用失败 → 直接返回错误 Observation
- ✅ 简单明确
- ❌ 健壮性较低

## 七、性能对比

### 7.1 连接开销

| 操作 | mcpbench_dev | OpenHands SDK |
|------|--------------|---------------|
| **初始化** | 一次性连接所有服务器 | 不连接 |
| **首次调用** | 直接调用（已连接） | 连接 + 调用 |
| **后续调用** | 直接调用 | 重新连接 + 调用 |
| **10 次调用** | 1 次连接 + 10 次调用 | 10 次连接 + 10 次调用 |
| **100 次调用** | 1 次连接 + 100 次调用 | 100 次连接 + 100 次调用 |

**估算**：
- 连接开销：~100-500ms
- 调用开销：~10-100ms

**10 次调用**：
- mcpbench_dev: 500ms + 10 × 50ms = **1000ms**
- OpenHands: 10 × (500ms + 50ms) = **5500ms**

**100 次调用**：
- mcpbench_dev: 500ms + 100 × 50ms = **5500ms**
- OpenHands: 100 × (500ms + 50ms) = **55000ms (55秒)**

### 7.2 内存占用

| 方面 | mcpbench_dev | OpenHands SDK |
|------|--------------|---------------|
| **连接对象** | 持久化（常驻内存） | 按需创建/销毁 |
| **状态管理** | 4 个字典 + 任务 | 无状态 |
| **工具列表缓存** | 可选缓存 | 一次性获取 |
| **典型内存** | ~50-100MB | ~10-20MB |

### 7.3 适用场景

**mcpbench_dev 适合**：
- ✅ 需要频繁调用同一工具
- ✅ 长时间运行的任务
- ✅ 需要查询连接状态
- ✅ 对性能要求高

**OpenHands SDK 适合**：
- ✅ 偶尔调用工具
- ✅ 短期任务
- ✅ 简单场景
- ✅ 无状态设计

## 八、迁移方案

### 8.1 保留 mcpbench_dev 的 MCPServerManager

**推荐方案**：保留现有的 MCP 管理，只在 Agent 初始化时适配

```python
# 在 task_agent.py 中
class TaskAgent:
    async def setup_mcp_servers(self):
        """保留原有的 MCP 管理"""
        self.mcp_manager = MCPServerManager(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,
            debug=self.debug,
            local_token_key_session=self.task_config.local_token_key_session
        )
        await self.mcp_manager.connect_servers(self.task_config.needed_mcp_servers)

    async def setup_agent(self):
        """创建 OpenHands Agent，但不使用其 MCP 功能"""
        # 创建 LLM
        self.llm = LLM(...)

        # 注册本地工具
        tool_specs = [...]

        # 创建 Agent（不传递 mcp_config）
        self.agent = Agent(
            llm=self.llm,
            tools=tool_specs,
            mcp_config={},  # 空，不使用 OpenHands 的 MCP
        )

        # 手动添加 MCP 工具（从 MCPServerManager）
        await self._add_mcp_tools_from_manager()

    async def _add_mcp_tools_from_manager(self):
        """将 MCPServerManager 的工具转换为 OpenHands MCPTool"""
        for server_name, server in self.mcp_manager.connected_servers.items():
            # 获取工具列表
            mcp_tools = await server.list_tools()

            for mcp_tool in mcp_tools:
                # 创建适配器工具
                tool = MCPToolAdapter(
                    name=mcp_tool.name,
                    description=mcp_tool.description,
                    server=server,  # 使用已连接的服务器
                    mcp_tool=mcp_tool
                )

                # 添加到 Agent
                self.agent._tools[tool.name] = tool
```

### 8.2 创建适配器

**MCPToolAdapter**：桥接两个系统
```python
class MCPToolAdapter(Tool):
    """适配器：使用 mcpbench 的连接服务器，符合 OpenHands 接口"""

    def __init__(self, name, description, server, mcp_tool):
        self.server = server  # MCPServerStdio（已连接）
        self.mcp_tool_def = mcp_tool

        super().__init__(
            name=name,
            description=description,
            action_type=MCPToolAction,
            observation_type=MCPToolObservation,
            executor=MCPToolAdapterExecutor(server=server, tool_name=name)
        )

class MCPToolAdapterExecutor(ToolExecutor):
    """执行器：直接调用已连接的服务器"""

    def __init__(self, server, tool_name):
        self.server = server
        self.tool_name = tool_name

    def __call__(self, action: MCPToolAction) -> MCPToolObservation:
        """同步调用（服务器已连接）"""
        # 直接调用，无需重新连接
        result = asyncio.run(
            call_tool_with_retry(
                server=self.server,
                tool_name=self.tool_name,
                arguments=action.to_mcp_arguments(),
                retry_time=5
            )
        )

        return MCPToolObservation.from_call_tool_result(
            tool_name=self.tool_name,
            result=result
        )
```

### 8.3 优势

**这种方案的好处**：
- ✅ 保留 mcpbench_dev 的所有优势（模板、重试、持久连接）
- ✅ 使用 OpenHands 的 Agent/Conversation 框架
- ✅ 最小化改动
- ✅ 性能最优

**需要修改的文件**：
1. `utils/roles/task_agent.py` - 添加适配逻辑（~100 行）
2. `utils/openhands_adapter/mcp_tool_adapter.py` - 新建适配器（~150 行）
3. 其他文件无需改动

## 九、总结对比表

| 特性 | mcpbench_dev | OpenHands SDK | 推荐迁移方案 |
|------|--------------|---------------|-------------|
| **配置方式** | YAML + 模板 | 内联 Dict | 保留 YAML |
| **模板系统** | ✅ 强大 | ❌ 无 | 保留 |
| **Task-specific Token** | ✅ 支持 | ❌ 无 | 保留 |
| **连接模式** | 持久连接 | 按需连接 | 保留持久连接 |
| **重试机制** | ✅ 多层 | ❌ 无 | 保留 |
| **性能** | ⚡ 高 | 🐌 低 | 保留高性能 |
| **状态管理** | 显式 | 隐式 | 保留显式 |
| **工具过滤** | 按服务器 | 按工具名 | 保留按服务器 |
| **使用复杂度** | 中等 | 简单 | - |
| **灵活性** | 高 | 低 | 保留高灵活性 |

## 十、推荐的迁移策略

### 🎯 最佳实践：混合方案

1. **保留 mcpbench_dev 的 MCP 管理**
   - 完整保留 `MCPServerManager`
   - 保留 YAML 配置系统
   - 保留模板变量系统
   - 保留持久连接机制

2. **采用 OpenHands 的 Agent 框架**
   - 使用 `Agent` + `Conversation`
   - 使用事件系统
   - 使用 `Condenser`

3. **创建适配层**
   - `MCPToolAdapter` 桥接两个系统
   - Agent 使用适配后的工具
   - 保持接口兼容性

**工作量估算**：
- 创建适配器：1-2 天
- 集成测试：1 天
- **总计：2-3 天**

**迁移文件清单**：
```
新增：
  utils/openhands_adapter/mcp_tool_adapter.py  (~150 行)

修改：
  utils/roles/task_agent.py  (~100 行改动)
    - 修改 setup_agent() 方法
    - 添加 _add_mcp_tools_from_manager() 方法

保留（无需改动）：
  utils/mcp/tool_servers.py  (完整保留)
  configs/mcp_servers/*.yaml  (完整保留)
  configs/token_key_session.py  (完整保留)
```

这种方案能够**保留 mcpbench_dev 的所有优势，同时享受 OpenHands 的现代架构**！
