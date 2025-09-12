# Notion API 调试工具使用指南

## 🎯 功能概览

这个调试工具提供两种主要功能：
1. **从页面 ID 查找数据库 ID** - 解决"只知道页面ID，想找数据库ID"的问题
2. **查询数据库内容** - 调试数据库查询和数据结构

## 📋 使用方法

### 1. 从页面 ID 查找数据库 ID

当您只有 Notion 页面 URL 或页面 ID 时，使用这个功能找到页面中的所有数据库：

```bash
# 方法1: 使用配置文件中的token
python debug_notion.py find <page_id>

# 方法2: 手动提供token
python debug_notion.py find <page_id> <notion_token>

# 示例
python debug_notion.py find 23dc4171366e803c832de1eb28b8424e
```

**输出示例：**
```
🔍 查找模式：从页面ID查找数据库
📄 页面 ID: 23dc4171366e803c832de1eb28b8424e
═══════════════════════════════════════════════════════════
🔍 获取页面信息
📄 页面 ID: 23dc4171366e803c832de1eb28b8424e
✅ 成功获取页面信息
📋 页面标题: MCPTestPage
📦 块 1: child_database (ID: 26bc4171366e81b8ba4fda2df2c72c29)
   🎯 找到内联数据库: 26bc4171366e81b8ba4fda2df2c72c29
═══════════════════════════════════════════════════════════
🎉 查找完成！
📊 找到 1 个数据库
   1. 26bc4171366e81b8ba4fda2df2c72c29
```

### 2. 查询数据库内容

有了数据库 ID 后，可以查询数据库的具体内容：

```bash
# 方法1: 使用配置文件中的token
python debug_notion.py <database_id>

# 方法2: 手动提供token
python debug_notion.py <database_id> <notion_token>

# 示例
python debug_notion.py 26bc4171366e81b8ba4fda2df2c72c29
```

### 3. 使用默认配置

如果不提供任何参数，工具会使用配置文件中的默认设置：

```bash
python debug_notion.py
```

## 🔧 从 URL 提取页面/数据库 ID

### Notion URL 格式分析

#### 页面 URL
```
https://www.notion.so/23dc4171366e803c832de1eb28b8424e
```
- **页面 ID**: `23dc4171366e803c832de1eb28b8424e`

#### 数据库 URL
```
https://www.notion.so/26bc4171366e81b8ba4fda2df2c72c29?v=26bc4171366e818e87c5000ca3ce6d46
```
- **数据库 ID**: `26bc4171366e81b8ba4fda2df2c72c29`
- **视图 ID**: `26bc4171366e818e87c5000ca3ce6d46`

### ID 格式转换

Notion ID 通常有两种格式：
1. **短格式** (URL中): `26bc4171366e81b8ba4fda2df2c72c29`
2. **长格式** (API中): `26bc4171-366e-81b8-ba4f-da2df2c72c29`

工具会自动处理这两种格式。

## 📁 输出文件

### 查找数据库时
- 文件名: `debug_page_{page_id}_databases.json`
- 内容: 页面信息和找到的数据库ID列表

### 查询数据库时
- 文件名: `debug_database_{database_id}_results.json`
- 内容: 数据库的所有记录

## 🔍 常见用例

### 用例 1: 从 Notion URL 开始
```bash
# 1. 从 Notion URL 提取页面 ID
URL: https://www.notion.so/MCPTestPage-23dc4171366e803c832de1eb28b8424e
页面 ID: 23dc4171366e803c832de1eb28b8424e

# 2. 查找页面中的数据库
python debug_notion.py find 23dc4171366e803c832de1eb28b8424e

# 3. 查询找到的数据库
python debug_notion.py 26bc4171366e81b8ba4fda2df2c72c29
```

### 用例 2: 调试 API 错误
当遇到 Notion API 错误时，使用这个工具可以：
- 详细查看API请求和响应
- 检查数据库结构
- 验证权限和访问
- 分析数据格式

### 用例 3: 数据库迁移
在迁移或备份数据库时：
- 导出完整的数据库内容
- 分析数据结构
- 验证数据完整性

## ⚙️ 配置要求

### Token 配置文件
在以下位置创建 `token_key_session.py`：
- `configs/token_key_session.py`
- `../../configs/token_key_session.py`
- `../../../configs/token_key_session.py`

文件内容：
```python
class TokenKeySession:
    def __init__(self):
        self.notion_integration_key = "your_notion_token_here"

all_token_key_session = TokenKeySession()
```

### 权限要求
确保 Notion integration 有以下权限：
- **Read content**: 读取页面和数据库内容
- **Read user information**: 获取用户信息（如果需要）

## 🚨 故障排除

### 常见错误

#### 1. "Get page failed: 404"
- 页面 ID 不正确
- Integration 没有访问该页面的权限
- 页面已被删除

#### 2. "Get blocks failed: 403"
- Integration 没有读取页面块内容的权限
- 需要在 Notion 中重新授权

#### 3. "Notion query failed: 401"
- Token 无效或过期
- 检查 `token_key_session.py` 配置

#### 4. "未找到任何数据库"
- 页面中确实没有数据库
- 数据库可能在子页面中
- 数据库可能是链接形式

### 调试技巧

1. **开启详细输出**: 工具默认开启详细调试信息
2. **检查输出文件**: 所有结果都保存为 JSON 文件
3. **分段调试**: 先用 `find` 模式，再用数据库查询模式
4. **网络问题**: 检查网络连接和代理设置

## 📞 支持

如果遇到问题：
1. 检查 Notion API 文档
2. 验证 Token 权限
3. 查看详细错误输出
4. 检查输出的 JSON 文件结构 