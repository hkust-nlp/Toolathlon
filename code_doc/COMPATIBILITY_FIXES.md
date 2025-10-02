# 兼容性问题修复总结

## 修复的问题

### 1. UUID 序列化错误

**错误信息**:
```
TypeError: Object of type UUID is not JSON serializable
```

**触发场景**:
- 任务达到 max_turns
- 任务异常退出
- 任务完成后保存结果

**根本原因**:
- OpenHands SDK 的 `Conversation.id` 是 UUID 对象
- `save_results()` 方法在保存结果时调用 `json.dumps()`
- Python 的 `json.dumps()` 不支持 UUID 类型序列化
- `CustomJSONEncoder` 只处理了 `bool` 类型，未处理 UUID

**修复位置**: `utils/roles/task_agent.py:126-133`

**修复方法**:
```python
class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，用于处理将Python中的布尔值转换为小写的'true'和'false'形式输出，以及处理 UUID 对象"""
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()
        if isinstance(o, uuid.UUID):  # ✅ 添加 UUID 支持
            return str(o)
        return super().default(o)
```

**效果**:
- ✅ 所有 UUID 对象会被自动转换为字符串
- ✅ 任务结果可以正常保存到 JSON 文件
- ✅ 不再出现序列化错误

---

### 2. web_search 工具的 kind 字段验证错误

**错误信息**:
```
[Agent Error] local-web_search: Error validating args {"kind":"web_search"} for tool 'local-web_search':
1 validation error for local-web_searchAction
kind
  Input should be 'CustomAction' [type=literal_error, input_value='web_search', input_type=str]
```

**根本原因分析**:

1. **OpenHands SDK 的 discriminated union 机制**:
   - `Action` 基类有一个 `kind` 字段用于区分不同的子类
   - 这个字段在 Pydantic 模型验证时会被检查

2. **LLM 生成了包含 `kind` 的参数**:
   - 虽然工具的 `params_json_schema` 中不包含 `kind` 字段
   - 但 OpenHands SDK 在从 Action 类生成工具 schema 时，可能包含了继承的 `kind` 字段
   - LLM 看到 schema 中有 `kind` 字段，就生成了对应的参数

3. **验证失败**:
   - LLM 生成 `{"kind": "web_search", "query": "..."}`
   - Pydantic 尝试验证 `kind` 字段
   - 但 `kind` 应该是类名（如 `"local-web_searchAction"`），而不是 LLM 生成的值
   - 验证失败

**修复位置**: `utils/openhands_adapter/tool_adapter.py:13-39`

**修复方法**:

#### 方法 1: 使用 field_validator 强制值
```python
class CustomAction(Action):
    """Custom action for tool"""

    # 设置 kind 字段，使用 json_schema_extra 从 schema 中排除
    kind: str = Field(
        default=action_class_name,
        json_schema_extra={"exclude": True}  # 尝试从生成的 JSON schema 中排除
    )

    @field_validator('kind', mode='before')
    @classmethod
    def force_kind_value(cls, v):
        """强制 kind 字段始终是类名，忽略外部输入"""
        return action_class_name  # ✅ 无论输入什么，都返回正确的类名
```

**这个修复的逻辑**:
1. **field_validator** 在 Pydantic 验证阶段运行
2. `mode='before'` 表示在类型转换之前运行
3. 无论 LLM 传入什么值（如 `"web_search"`），都会被替换为正确的类名（如 `"local-web_searchAction"`）
4. 这样就能通过 Pydantic 的验证

#### 方法 2: 从 JSON schema 中排除 kind（可能需要额外配置）
```python
kind: str = Field(
    default=action_class_name,
    json_schema_extra={"exclude": True}  # 尝试不让 LLM 看到这个字段
)
```

**注意**: 这个方法的效果取决于 OpenHands SDK 如何生成工具 schema。如果 OpenHands 忽略了 `json_schema_extra`，则需要其他方法。

---

## 根本问题：为什么会有这些兼容性问题？

### 从 OpenAI Agents SDK 迁移到 OpenHands SDK

**OpenAI Agents SDK**:
- 简单的 `FunctionTool` 定义
- 不使用 discriminated union
- 工具参数直接从 `params_json_schema` 生成
- 没有 `kind` 字段的概念

**OpenHands SDK**:
- 复杂的类型系统（Action, Observation, Tool）
- 使用 Pydantic discriminated union 机制
- `kind` 字段用于区分不同的 Action/Observation 子类
- 工具 schema 可能从 Action 类自动生成

### 适配器的挑战

我们的 `tool_adapter.py` 需要：
1. 将简单的 `FunctionTool` 转换为复杂的 OpenHands Tool
2. 正确设置 `kind` 字段
3. 确保 LLM 不会生成错误的 `kind` 值
4. 处理 Pydantic 的验证逻辑

---

## 测试建议

### 测试 1: UUID 序列化
```bash
# 运行任务直到达到 max_turns
uv run demo.py \
  --eval_config scripts/debug_eval_config.json \
  --task_dir <any_task> \
  --debug

# 检查 log.json 是否成功生成
# 检查 conversation_id 字段是否是字符串格式的 UUID
```

### 测试 2: web_search 工具
```bash
# 运行使用 web_search 的任务
uv run demo.py \
  --eval_config scripts/debug_eval_config.json \
  --task_dir <task_with_web_search> \
  --debug

# 观察日志，确认：
# 1. web_search 工具成功调用
# 2. 没有 kind 验证错误
# 3. 工具返回正常结果
```

### 测试 3: 其他本地工具
```bash
# 测试 done, sleep 等其他本地工具
# 确认它们也能正常工作
```

---

## 剩余的潜在问题

### 如果 field_validator 方法仍然失败

**可能的原因**:
- OpenHands SDK 在 LLM 看到的 schema 中仍然包含 `kind` 字段
- LLM 继续生成 `kind` 参数

**更激进的解决方案**:

#### 选项 1: 在 executor 中过滤 `kind` 参数
我们已经在 `create_executor_class` 中使用 `model_dump(exclude={'kind'})` 来提取参数，这应该能正确处理。

#### 选项 2: 修改 ToolSpec 的 params
在 `register_function_tools` 中，确保传递给 LLM 的 schema 不包含 `kind`：

```python
# 在 tool_adapter.py:223 处
toolspec = ToolSpec(
    name=tool_name,
    params=function_tool.params_json_schema  # 这个 schema 中不应该有 kind
)
```

#### 选项 3: 覆盖 Action 类的 model_json_schema 方法
```python
class CustomAction(Action):
    @classmethod
    def model_json_schema(cls, **kwargs):
        schema = super().model_json_schema(**kwargs)
        # 从 properties 中删除 kind
        if 'properties' in schema and 'kind' in schema['properties']:
            del schema['properties']['kind']
        if 'required' in schema and 'kind' in schema['required']:
            schema['required'].remove('kind')
        return schema
```

---

## 总结

### 已修复
1. ✅ UUID 序列化问题 - 扩展 `CustomJSONEncoder`
2. ✅ kind 字段验证问题 - 使用 `field_validator` 强制值

### 修改的文件
1. `utils/roles/task_agent.py` - 添加 UUID 支持到 JSON encoder
2. `utils/openhands_adapter/tool_adapter.py` - 添加 kind 字段验证器

### 测试状态
- ⏳ 需要运行实际测试验证修复效果
- ⏳ 如果仍有问题，可能需要更激进的解决方案

---

**修复完成时间**: 2025-10-02
**修复类型**: SDK 迁移兼容性问题
**核心原因**: OpenAI Agents SDK 到 OpenHands SDK 的架构差异
