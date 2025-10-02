# OpenHands MCPTool 兼容性修复

## 问题描述

在实际运行时遇到错误：
```
AttributeError: 'MCPTool' object has no attribute 'params_json_schema'
```

## 根本原因

**OpenHands MCPTool** 和 **mcpbench_dev 原有 Tool** 对象有不同的 API：

### OpenHands MCPTool
```python
# 使用 to_openai_tool() 方法获取工具定义
tool.to_openai_tool()  # 返回 ChatCompletionToolParam
# 返回格式:
# {
#     "type": "function",
#     "function": {
#         "name": "read_file",
#         "description": "...",
#         "parameters": {...}  # JSON Schema
#     }
# }
```

### mcpbench_dev 原有 Tool
```python
# 直接访问 params_json_schema 属性
tool.params_json_schema  # 返回 JSON Schema dict
```

## 解决方案

修改 `task_agent.py` 的 `setup_agent()` 方法（第 525-557 行），添加兼容逻辑：

### 修改前
```python
for tool in available_tools:
    self.all_tools.append({
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.params_json_schema  # ❌ MCPTool 没有此属性
        }
    })
```

### 修改后
```python
for tool in available_tools:
    # 兼容 OpenHands MCPTool 和原有 Tool 对象
    if hasattr(tool, 'to_openai_tool'):
        # OpenHands MCPTool - 使用 to_openai_tool() 方法
        openai_tool = tool.to_openai_tool()
        self.all_tools.append(openai_tool)
    elif hasattr(tool, 'params_json_schema'):
        # 原有 Tool 对象 - 使用 params_json_schema 属性
        self.all_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.params_json_schema
            }
        })
    else:
        # 兜底：构建基本的工具定义
        self.all_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {"type": "object", "properties": {}}
            }
        })
```

## 兼容性说明

这个修改确保 TaskAgent 可以同时支持：

1. ✅ **OpenHands MCPTool** - 从 OpenHands SDK 创建的 MCP 工具
2. ✅ **mcpbench_dev 原有 Tool** - 本地工具（如 `tool_sleep`, `tool_done` 等）
3. ✅ **未知格式工具** - 兜底处理，使用空参数 schema

## 技术细节

### OpenHands MCPTool 结构
```python
class MCPTool(Tool[MCPToolAction, MCPToolObservation]):
    mcp_tool: mcp.types.Tool  # 原始 MCP 工具定义

    def to_openai_tool(self) -> ChatCompletionToolParam:
        """转换为 OpenAI 工具格式"""
        return ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name=self.name,
                description=self.description,
                parameters=self.action_type.to_mcp_schema()  # 从 MCP schema 转换
            )
        )
```

### mcpbench_dev Tool 结构
```python
class Tool:
    name: str
    description: str
    params_json_schema: dict  # 直接存储 JSON Schema
```

## 测试验证

修复后，TaskAgent 应该能够：

1. ✅ 加载 OpenHands MCP 工具（filesystem, github 等）
2. ✅ 加载本地工具（sleep, done, manage_context 等）
3. ✅ 正确构建 `self.all_tools` 列表
4. ✅ 传递给 User simulator 和其他需要工具列表的组件

## 相关文件

- **修改文件**: `mcpbench_dev/utils/roles/task_agent.py` (第 525-557 行)
- **相关类**:
  - `openhands.sdk.mcp.tool.MCPTool`
  - `openhands.sdk.tool.tool.Tool`

## 影响范围

这是一个向后兼容的修复：
- ✅ 不影响原有本地工具的使用
- ✅ 支持 OpenHands MCP 工具
- ✅ 不破坏现有功能

---

**修复状态**: ✅ 已完成
**测试状态**: ⏳ 待实际运行验证
