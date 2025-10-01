# 参数映射：OpenAI Agents SDK → OpenHands SDK

## 问题描述

在替换过程中发现 OpenHands SDK 的 LLM 类使用不同的参数名称。

### 报错信息
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for LLM
max_tokens
  Extra inputs are not permitted [type=extra_forbidden, input_value=4096, input_type=int]
```

## 参数映射表

| 原框架参数 | OpenHands 参数 | 说明 | 状态 |
|-----------|---------------|------|------|
| `temperature` | `temperature` | 温度参数 | ✅ 直接映射 |
| `max_tokens` | `max_output_tokens` | 最大生成 token 数 | ✅ 已修复 |
| `top_p` | `top_p` | Top-p 采样 | ✅ 直接映射 |
| `top_k` | `top_k` | Top-k 采样 | ✅ 可选 |

## 修复方案

在 `utils/openhands_adapter/llm_adapter.py` 中：

```python
# 修改前
llm_config: Dict[str, Any] = {
    "model": model_name,
    "temperature": temperature,
    "max_tokens": max_tokens,  # ❌ 不支持
    "top_p": top_p,
}

# 修改后
llm_config: Dict[str, Any] = {
    "model": model_name,
    "temperature": temperature,
    "max_output_tokens": max_tokens,  # ✅ 正确参数
    "top_p": top_p,
}
```

## OpenHands LLM 支持的额外参数

以下是 OpenHands LLM 支持但原框架未使用的参数：

### 1. Token 限制
- `max_input_tokens`: 最大输入 token 数
- `max_output_tokens`: 最大输出 token 数（已使用）

### 2. 重试配置
- `num_retries`: 重试次数（默认: 8）
- `retry_multiplier`: 重试倍增系数（默认: 2.0）
- `retry_min_wait`: 最小等待时间（默认: 1 秒）
- `retry_max_wait`: 最大等待时间（默认: 10 秒）
- `timeout`: 超时时间

### 3. API 配置
- `api_key`: API 密钥
- `base_url`: API 基础 URL
- `api_version`: API 版本
- `custom_llm_provider`: 自定义 LLM 提供商

### 4. AWS 配置
- `aws_access_key_id`: AWS 访问密钥
- `aws_secret_access_key`: AWS 密钥
- `aws_region_name`: AWS 区域

### 5. 功能开关
- `disable_vision`: 禁用视觉功能
- `disable_stop_word`: 禁用停止词
- `native_tool_calling`: 原生工具调用
- `caching_prompt`: 提示缓存
- `drop_params`: 丢弃不支持的参数
- `modify_params`: 修改参数

### 6. 其他
- `seed`: 随机种子
- `reasoning_effort`: 推理强度（'low', 'medium', 'high', 'none'）
- `extended_thinking_budget`: 扩展思考预算
- `safety_settings`: 安全设置

## 配置示例

### 原框架配置（eval_config.json）
```json
{
  "agent": {
    "generation": {
      "temperature": 0.6,
      "top_p": 1.0,
      "max_tokens": 4096
    }
  }
}
```

### 映射后的 OpenHands LLM
```python
llm = LLM(
    model="claude-sonnet-4-20250514",
    temperature=0.6,
    top_p=1.0,
    max_output_tokens=4096,  # ← 注意参数名变化
    api_key=SecretStr("..."),
    base_url="https://..."
)
```

## 验证测试

```bash
uv run python -c "
from utils.openhands_adapter import create_openhands_llm_from_config
from utils.data_structures.agent_config import AgentConfig
import json

config = json.load(open('scripts/temp_and_debug/debug_eval_config.json'))
agent_config = AgentConfig.from_dict(config['agent'])

# ... 创建 mock provider ...

llm = create_openhands_llm_from_config(
    agent_config=agent_config,
    agent_model_provider=mock_provider,
    debug=False
)

print(f'✓ Max Output Tokens: {llm.max_output_tokens}')  # 应该是 4096
"
```

## 注意事项

1. **参数名称不同**: `max_tokens` → `max_output_tokens`
2. **向后兼容**: adapter 保持 `max_tokens` 作为输入参数名，内部自动映射
3. **Pydantic 验证**: OpenHands 使用严格的 Pydantic 模型，不允许额外字段
4. **输入限制**: 如需限制输入 token，使用 `max_input_tokens` 参数

## 相关文件

- `utils/openhands_adapter/llm_adapter.py` - LLM 适配器（已修复）
- `utils/roles/task_agent.py` - TaskAgent 类
- `scripts/temp_and_debug/debug_eval_config.json` - 测试配置

## 修复状态

- ✅ 参数映射完成
- ✅ 测试验证通过
- ✅ 文档更新完成
