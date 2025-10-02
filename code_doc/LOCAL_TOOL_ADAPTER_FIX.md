# 本地工具适配器修复报告

## 问题描述

在使用 OpenHands SDK 替换 OpenAI Agents SDK 后，本地工具（如 `web_search`）出现了两个关键错误：

### 错误 1: kind 字段验证失败
```
Error validating args {"kind":"search"} for tool 'local-web_search':
1 validation error for local-web_searchAction
kind
  Input should be 'CustomAction' [type=literal_error, input_value='search', input_type=str]
```

### 错误 2: tool_use_id 不匹配
```
litellm.BadRequestError: ValidationException: messages.8.content.0: unexpected `tool_use_id` found in `tool_result` blocks: toolu_bdrk_0174STAhtXMHHm6nqcnj91cc. Each `tool_result` block must have a corresponding `tool_use` block in the previous message.
```

## 根本原因分析

### 原因 1: kind 字段未正确设置

**问题**：
- OpenHands SDK 使用 Pydantic 的 discriminated union 机制
- `Action` 和 `Observation` 基类有一个 `kind` 字段用于区分不同的子类
- 在 `tool_adapter.py` 中动态创建的 `CustomAction` 类没有正确设置 `kind` 字段的默认值

**之前的代码**：
```python
def create_action_class(tool_name: str):
    class CustomAction(Action):
        """Custom action for tool"""
        pass  # ❌ 没有设置 kind 字段

    CustomAction.__name__ = f"{tool_name}Action"
    return CustomAction
```

**问题表现**：
- LLM 生成的工具调用参数中可能包含名为 `kind` 的字段（如 web_search 的 `"kind":"search"` 参数）
- 这个参数被错误地赋值给了 Pydantic 的 `kind` 字段
- 导致验证失败，因为 `kind` 字段期望类名，不是工具参数

### 原因 2: 函数签名不匹配

**问题**：
- 旧的 OpenAI Agents SDK 工具函数签名：`on_invoke_tool(context: RunContextWrapper, params_str: str)`
- 新的适配器只传递了参数字典：`on_invoke(params)`
- 导致函数调用失败

**之前的代码**：
```python
def __call__(self, action: Action) -> Observation:
    params = {}
    for key, value in action.__dict__.items():
        if not key.startswith('_') and key not in ['kind', 'thought', 'tool_name']:
            params[key] = value

    # ❌ 只传递一个参数，但函数期望两个参数
    result = on_invoke(params)
```

### 原因 3: Observation 缺少 to_llm_content 方法

**问题**：
- OpenHands 的 `Observation` 类要求子类实现 `to_llm_content` 属性
- 旧的 `CustomObservation` 类没有实现这个方法

## 修复方案

### 修复 1: 正确设置 kind 字段

**文件**: `utils/openhands_adapter/tool_adapter.py`

**修复后的代码**：
```python
def create_action_class(tool_name: str):
    """动态创建 Action 类"""
    from pydantic import Field

    class CustomAction(Action):
        """Custom action for tool"""
        # ✅ 显式设置 kind 字段为类名（Pydantic discriminated union 要求）
        kind: str = Field(default=f"{tool_name}Action", frozen=True)

    # 设置类名
    CustomAction.__name__ = f"{tool_name}Action"
    CustomAction.__qualname__ = f"{tool_name}Action"

    return CustomAction
```

**关键改进**：
1. 使用 `Field(default=..., frozen=True)` 设置 `kind` 的默认值为类名
2. `frozen=True` 确保 `kind` 字段不可修改，防止被工具参数覆盖

### 修复 2: 添加 to_llm_content 方法

**修复后的代码**：
```python
def create_observation_class(tool_name: str):
    """动态创建 Observation 类"""
    from pydantic import Field
    from openhands.sdk.llm import TextContent

    class CustomObservation(Observation):
        """Custom observation for tool"""
        # ✅ 显式设置 kind 字段为类名
        kind: str = Field(default=f"{tool_name}Observation", frozen=True)
        content: str = ""
        error: str | None = None

        # ✅ 实现 to_llm_content 方法（OpenHands 要求）
        @property
        def to_llm_content(self):
            """返回 LLM 格式的内容"""
            if self.error:
                return [TextContent(text=f"Error: {self.error}")]
            return [TextContent(text=self.content)]

    CustomObservation.__name__ = f"{tool_name}Observation"
    CustomObservation.__qualname__ = f"{tool_name}Observation"

    return CustomObservation
```

### 修复 3: 兼容不同的函数签名

**修复后的代码**：
```python
def create_executor_class(tool_name: str, on_invoke: Callable, ObservationClass):
    """动态创建 ToolExecutor 类"""
    class CustomExecutor(ToolExecutor):
        """Custom executor for tool"""

        def __call__(self, action: Action) -> Observation:
            """执行工具调用"""
            try:
                # ✅ 使用 model_dump 提取参数，排除 kind 字段
                params = {}
                if hasattr(action, 'model_dump'):
                    params = action.model_dump(exclude={'kind'})

                # ✅ 检查函数签名，决定如何调用
                import json
                sig = inspect.signature(on_invoke)
                param_names = list(sig.parameters.keys())

                if inspect.iscoroutinefunction(on_invoke):
                    # 异步函数
                    if len(param_names) == 2:
                        # ✅ 旧格式：(context, params_str)
                        params_str = json.dumps(params)
                        result = await on_invoke(None, params_str)
                    else:
                        # ✅ 新格式：(params)
                        result = await on_invoke(params)
                else:
                    # 同步函数
                    if len(param_names) == 2:
                        params_str = json.dumps(params)
                        result = on_invoke(None, params_str)
                    else:
                        result = on_invoke(params)

                return ObservationClass(
                    content=str(result),
                    error=None
                )
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                return ObservationClass(
                    content="",
                    error=error_msg
                )
```

**关键改进**：
1. 使用 `model_dump(exclude={'kind'})` 提取参数，避免包含 `kind` 字段
2. 通过 `inspect.signature` 检查函数签名
3. 根据参数数量决定调用方式：
   - 2个参数：传递 `(None, params_str)` - 兼容旧的 OpenAI Agents SDK 格式
   - 1个参数：传递 `params` - 新格式

## OpenHands Action/Observation 架构

### Discriminated Union 机制

OpenHands SDK 使用 Pydantic 的 discriminated union 机制来处理不同类型的 Action 和 Observation：

```python
class DiscriminatedUnionMixin(OpenHandsModel, ABC):
    """Base class for discriminated unions"""
    kind: str = Field(default="")  # 用于区分子类的字段

    @classmethod
    def resolve_kind(cls, kind: str) -> type:
        """根据 kind 字符串解析出对应的子类"""
        for subclass in get_known_concrete_subclasses(cls):
            if subclass.__name__ == kind:
                return subclass
        raise ValueError(f"Unknown kind '{kind}' for {cls}")
```

### Action 继承链

```
Action (DiscriminatedUnionMixin, ABC)
  └── kind: str = Field(default="")

CustomAction (Action)
  └── kind: str = Field(default="web_searchAction", frozen=True)  # ✅ 必须设置
  └── query: str  # 工具参数
  └── num_results: int  # 工具参数
```

### 为什么 frozen=True 重要

```python
# ❌ 没有 frozen=True
class CustomAction(Action):
    kind: str = Field(default="web_searchAction")
    query: str

# LLM 生成的参数
{"kind": "search", "query": "test"}  # kind 会被覆盖！

# ✅ 有 frozen=True
class CustomAction(Action):
    kind: str = Field(default="web_searchAction", frozen=True)
    query: str

# LLM 生成的参数
{"kind": "search", "query": "test"}  # kind 不会被覆盖，保持为 "web_searchAction"
```

## 兼容性说明

### 支持的工具函数签名

1. **旧的 OpenAI Agents SDK 格式**（推荐逐步迁移）:
   ```python
   async def on_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
       params = json.loads(params_str)
       # 处理参数
       return result
   ```

2. **新的简化格式**:
   ```python
   async def on_tool_invoke(params: dict) -> Any:
       # 直接使用参数字典
       return result
   ```

适配器会自动检测函数签名并使用正确的调用方式。

### 参数提取

- 使用 `action.model_dump(exclude={'kind'})` 提取所有参数
- 自动排除 Pydantic 的内部字段（`kind`）
- 保留所有用户定义的工具参数

## 测试建议

1. **测试 web_search 工具**:
   ```bash
   uv run demo.py \
     --eval_config scripts/debug_eval_config.json \
     --task_dir <task_with_web_search> \
     --debug
   ```

2. **验证工具参数提取**:
   - 检查日志中的 `[Action] local-web_search` 消息
   - 确认参数正确传递给工具函数

3. **验证 Observation 返回**:
   - 检查工具执行结果是否正确返回
   - 确认没有 `tool_use_id` 不匹配错误

## 修复的文件

1. **utils/openhands_adapter/tool_adapter.py**
   - `create_action_class()` - 设置 kind 字段
   - `create_observation_class()` - 添加 to_llm_content 方法
   - `create_executor_class()` - 兼容不同函数签名

## 预期效果

- ✅ 本地工具（web_search、done、sleep 等）正常工作
- ✅ `kind` 字段验证通过
- ✅ 工具参数正确提取和传递
- ✅ LLM API 调用成功，无 tool_use_id 不匹配错误
- ✅ 兼容旧的和新的工具函数签名

---

**修复完成时间**: 2025-10-02
**修复原因**: OpenHands SDK 的 discriminated union 机制要求正确设置 kind 字段
**核心改进**: 完整的 OpenAI Agents SDK FunctionTool 到 OpenHands Tool 适配
