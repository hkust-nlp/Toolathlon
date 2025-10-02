# OpenHands MCP 初始化完成指南

## ✅ 已完成的工作

### 1. YAML 到 OpenHands 配置转换器
**文件**: `mcpbench_dev/utils/mcp/openhands_mcp_config.py`

已创建完整的转换层，将现有的 YAML 配置转换为 OpenHands SDK 需要的 Dict 格式。

**核心功能**:
- ✅ 加载 YAML 配置文件
- ✅ 处理模板变量（`${agent_workspace}`, `${token.*}`, `${config.*}` 等）
- ✅ 转换为 OpenHands `mcpServers` 格式
- ✅ 支持 stdio 和 sse 两种服务器类型
- ✅ 保留特殊处理逻辑（如 playwright 的 `--no-sandbox`）

### 2. 测试验证
**文件**: `mcpbench_dev/test_openhands_mcp_config.py`

所有测试通过：
- ✅ 基础配置转换
- ✅ 模板变量替换
- ✅ 加载全部 39 个服务器配置
- ✅ OpenHands SDK 兼容性

## 📖 使用方法

### 方法 1: 直接创建 MCP Config（推荐）

在 TaskAgent 中使用：

```python
from utils.mcp.openhands_mcp_config import create_openhands_mcp_config

class TaskAgent:
    async def setup_mcp_servers(self):
        """使用 OpenHands 的方式初始化 MCP"""
        # 创建 OpenHands 格式的配置
        self.mcp_config = create_openhands_mcp_config(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,  # "configs/mcp_servers"
            server_names=self.task_config.needed_mcp_servers,  # 从 task_config 读取
            local_token_key_session=self.task_config.local_token_key_session,
            debug=self.debug
        )

        # 现在 self.mcp_config 可以直接传给 OpenHands Agent
        # 格式示例:
        # {
        #     "mcpServers": {
        #         "filesystem": {
        #             "command": "npx",
        #             "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
        #         },
        #         "github": {
        #             "command": "/path/to/github-mcp-server",
        #             "args": ["stdio"],
        #             "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}
        #         }
        #     }
        # }

    async def setup_agent(self):
        """创建 OpenHands Agent"""
        from openhands.sdk.agent.agent import Agent

        # 创建 LLM
        self.llm = LLM(...)

        # 注册本地工具
        local_tools = register_tools(...)

        # 创建 Agent，使用转换后的 MCP 配置
        self.agent = Agent(
            llm=self.llm,
            tools=local_tools,
            mcp_config=self.mcp_config  # 直接使用转换后的配置
        )
```

### 方法 2: 直接创建 MCP Tools

如果想直接获取工具列表：

```python
from utils.mcp.openhands_mcp_config import create_openhands_mcp_tools

class TaskAgent:
    async def setup_agent(self):
        # 方式 A: 直接创建工具（会自动连接并断开 MCP 服务器）
        mcp_tools = create_openhands_mcp_tools(
            agent_workspace=self.task_config.agent_workspace,
            server_names=self.task_config.needed_mcp_servers,
            local_token_key_session=self.task_config.local_token_key_session,
            timeout=30.0
        )

        # 合并工具
        all_tools = local_tools + mcp_tools

        # 创建 Agent（不传 mcp_config）
        self.agent = Agent(
            llm=self.llm,
            tools=all_tools,
            mcp_config={}  # 空配置
        )
```

## 🔄 配置转换示例

### 输入: YAML 配置
```yaml
# configs/mcp_servers/filesystem.yaml
type: stdio
name: filesystem
params:
  command: npx
  args:
    - "-y"
    - "@modelcontextprotocol/server-filesystem"
    - "${agent_workspace}"
client_session_timeout_seconds: 300
```

### 输出: OpenHands Dict
```python
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/tasks/task001/workspace"  # 已替换模板变量
      ]
    }
  }
}
```

## 🎯 与原有系统的兼容性

### ✅ 完全保留的功能
1. **YAML 配置文件** - 无需修改任何 YAML 文件
2. **模板变量系统** - 所有 `${}` 变量正常工作
3. **Token 优先级** - task-specific token 覆盖 global token
4. **特殊处理** - playwright 的 root 用户检测等逻辑保留

### ✅ 不需要修改的文件
- `configs/mcp_servers/*.yaml` - 所有配置文件
- `configs/token_key_session.py` - Token 配置
- `configs/global_configs.py` - 全局配置
- `tasks/*/token_key_session.py` - Task-specific token

### ⚠️ 主要变化
从 mcpbench_dev 的持久连接模式 → OpenHands 的按需连接模式

**原来的方式**（不再使用）：
```python
# 旧方式 - MCPServerManager
from utils.mcp.tool_servers import MCPServerManager

manager = MCPServerManager(...)
await manager.connect_servers(['filesystem', 'github'])  # 持久连接
server = manager.connected_servers['filesystem']
result = await server.call_tool(...)  # 直接调用
await manager.disconnect_servers()
```

**新的方式**（OpenHands）：
```python
# 新方式 - 通过配置转换
from utils.mcp.openhands_mcp_config import create_openhands_mcp_config

mcp_config = create_openhands_mcp_config(...)  # 只创建配置
agent = Agent(llm=llm, tools=[], mcp_config=mcp_config)  # Agent 管理连接
# 每次工具调用时自动连接/断开
```

## 📝 下一步工作

要完全替换 TaskAgent 中的 MCP 管理，需要：

1. **修改 `utils/roles/task_agent.py`**:
   - 导入 `create_openhands_mcp_config`
   - 修改 `setup_mcp_servers()` 方法使用新的转换器
   - 修改 `setup_agent()` 方法传递转换后的配置

2. **示例修改**:
```python
# task_agent.py

from utils.mcp.openhands_mcp_config import create_openhands_mcp_config
from openhands.sdk.agent.agent import Agent

class TaskAgent:
    async def setup_mcp_servers(self, local_token_key_session: dict = None):
        """Setup MCP servers using OpenHands format"""
        self.mcp_config = create_openhands_mcp_config(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,
            server_names=self.task_config.needed_mcp_servers,
            local_token_key_session=local_token_key_session,
            debug=self.debug
        )

        if self.debug:
            print(f"Created OpenHands MCP config for {len(self.mcp_config['mcpServers'])} servers")

    async def setup_agent(self):
        """Setup OpenHands Agent"""
        # ... LLM setup ...
        # ... local tools setup ...

        self.agent = Agent(
            llm=self.llm,
            tools=local_tools,
            mcp_config=self.mcp_config  # 使用转换后的配置
        )
```

## 🧪 测试

运行测试验证配置转换：
```bash
cd mcpbench_dev
uv run python test_openhands_mcp_config.py
```

所有测试应该通过 ✅

## 📚 相关文件

- **转换器实现**: `utils/mcp/openhands_mcp_config.py`
- **测试脚本**: `test_openhands_mcp_config.py`
- **原有管理器**: `utils/mcp/tool_servers.py` (保留不动)
- **配置文件**: `configs/mcp_servers/*.yaml` (无需修改)

---

**总结**: MCP 初始化部分已完成，现在可以在 OpenHands SDK 中使用 mcpbench_dev 的所有 YAML 配置，同时保留模板变量系统的全部功能。
