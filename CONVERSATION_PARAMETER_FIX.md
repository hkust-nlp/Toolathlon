# Conversation 参数修复

## 问题

```
TypeError: Conversation.__new__() got an unexpected keyword argument 'working_dir'
```

## 原因

OpenHands SDK 的 `Conversation` 类使用 `workspace` 参数，而不是 `working_dir`。

## Conversation 完整参数列表

```python
Conversation(
    agent: AgentBase,
    *,
    workspace: str | LocalWorkspace | RemoteWorkspace = 'workspace/project',
    persistence_dir: str | None = None,
    conversation_id: UUID | None = None,
    callbacks: list[Callable[[Event], None]] | None = None,
    max_iteration_per_run: int = 500,
    stuck_detection: bool = True,
    visualize: bool = True,
    secrets: dict[str, str] | None = None
)
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `agent` | AgentBase | 必需 | Agent 实例 |
| `workspace` | str \| LocalWorkspace \| RemoteWorkspace | 'workspace/project' | 工作空间路径或对象 |
| `persistence_dir` | str \| None | None | 持久化目录（保存对话状态）|
| `conversation_id` | UUID \| None | None | 对话 ID（用于恢复）|
| `callbacks` | list[Callable] \| None | None | 事件回调函数列表 |
| `max_iteration_per_run` | int | 500 | 每次运行的最大迭代次数 |
| `stuck_detection` | bool | True | 是否启用卡住检测 |
| `visualize` | bool | True | 是否启用可视化 |
| `secrets` | dict[str, str] \| None | None | 密钥字典 |

## 修复

### 修改前（错误）
```python
self.conversation = Conversation(
    agent=self.agent,
    working_dir=str(self.task_config.agent_workspace),  # ❌ 错误参数名
    persistence_dir=str(persistence_dir),
    max_iteration_per_run=self.agent_config.tool.max_inner_turns,
    callbacks=[self._on_event],
    visualize=False,
)
```

### 修改后（正确）
```python
self.conversation = Conversation(
    agent=self.agent,
    workspace=str(self.task_config.agent_workspace),  # ✅ 正确参数名
    persistence_dir=str(persistence_dir),
    max_iteration_per_run=self.agent_config.tool.max_inner_turns,
    callbacks=[self._on_event],
    visualize=False,
)
```

## 我们使用的参数

根据 mcpbench_dev 的需求，我们使用：

- ✅ `agent`: OpenHands Agent 实例
- ✅ `workspace`: Agent 工作空间路径
- ✅ `persistence_dir`: 对话状态持久化目录
- ✅ `max_iteration_per_run`: 内部循环最大迭代次数
- ✅ `callbacks`: 事件回调（用于记录和统计）
- ✅ `visualize=False`: 禁用可视化（命令行模式）

## 未使用的参数

- `conversation_id`: 不需要（每次都是新对话）
- `stuck_detection`: 使用默认值 `True`
- `secrets`: 不需要（API keys 通过 LLM 配置传递）

## workspace 参数的三种形式

### 1. 字符串路径（我们使用的）
```python
workspace=str(self.task_config.agent_workspace)
# 例如: "/path/to/workspace"
```

### 2. LocalWorkspace 对象
```python
from openhands.sdk.workspace.local import LocalWorkspace

workspace = LocalWorkspace(path="/path/to/workspace")
```

### 3. RemoteWorkspace 对象
```python
from openhands.sdk.workspace.remote import RemoteWorkspace

workspace = RemoteWorkspace(
    url="https://remote-workspace.com",
    token="..."
)
```

## 相关文档

- 原始代码位置: `utils/roles/task_agent.py:528`
- OpenHands SDK: `openhands.sdk.conversation.Conversation`

## 修复状态

- ✅ 参数名称已修复
- ✅ 测试验证通过
- ✅ 文档已更新
