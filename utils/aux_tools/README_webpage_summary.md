# 网页AI总结工具使用说明

## 功能概述

这个工具可以自动抓取网页内容并使用AI模型进行智能总结，支持处理静态和动态网页内容。

## 主要特性

### 1. 智能网页抓取
- **静态内容抓取**: 使用 `requests` 库快速获取静态网页内容
- **动态内容处理**: 使用 `Playwright` 处理JavaScript动态加载的内容（比Selenium性能更强）
- **自动重试机制**: 最多重试3次，支持指数退避
- **内容清理**: 自动移除广告、导航等无关内容，提取核心文本
- **智能等待**: 自动等待网络空闲和页面稳定，确保内容完整加载

### 2. 内容提取优化
- 提取标题、段落、列表等结构化内容
- 保留重要链接信息
- 自动清理多余空白字符和格式
- 智能判断内容质量，自动选择最佳抓取方式

### 3. AI智能总结
- 使用GPT-4.1-nano模型进行内容总结
- 支持自定义总结长度（最大16000 tokens）
- 中文友好的提示词设计

## 使用方法

### 基本使用

```python
import asyncio
from utils.aux_tools.ai_webpage_summary import on_ai_webpage_summary_tool_invoke

async def summarize_webpage():
    # 模拟工具调用
    params = {
        "url": "https://example.com",
        "max_tokens": 500
    }
    
    # 注意：实际使用时需要传入真实的RunContextWrapper
    result = await on_ai_webpage_summary_tool_invoke(mock_context, json.dumps(params))
    print(result)

# 运行
asyncio.run(summarize_webpage())
```

### 单独使用网页抓取功能

```python
import asyncio
from utils.aux_tools.ai_webpage_summary import fetch_url_content

async def get_webpage_content():
    try:
        content = await fetch_url_content("https://example.com")
        print(f"网页内容长度: {len(content)}")
        print(f"内容预览: {content[:200]}...")
    except Exception as e:
        print(f"抓取失败: {e}")

# 运行
asyncio.run(get_webpage_content())
```

## 参数说明

### ai_webpage_summary 工具参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | - | 要总结的网页URL |
| max_tokens | number | 否 | 1000 | 总结的最大token数，最大16000 |

## 错误处理

工具会返回以下类型的错误信息：

- `Error: URL参数不能为空` - URL参数缺失
- `Error: 无效的URL格式` - URL格式错误
- `Error: 请求失败: [具体错误]` - 网络请求失败
- `Error: 无法获取有效的网页内容` - 内容抓取失败
- `Error: Playwright未安装，无法处理动态内容` - 缺少Playwright依赖
- `Error: 处理过程中出现未知错误: [具体错误]` - 其他未知错误

## 依赖要求

### 必需依赖
- `requests` - HTTP请求库
- `beautifulsoup4` - HTML解析库
- `lxml` - XML/HTML解析器

### 可选依赖
- `playwright` - 动态内容处理（用于JavaScript渲染的网页）

### 安装命令

```bash
# 安装必需依赖
pip install requests beautifulsoup4 lxml

# 安装可选依赖（用于动态内容）
pip install playwright

# 安装Playwright浏览器
playwright install chromium
```

## 性能优化建议

1. **静态网页优先**: 工具会首先尝试使用requests抓取，速度更快
2. **Playwright优势**: 相比Selenium，Playwright启动更快、内存占用更少、支持更多现代Web特性
3. **内容长度限制**: 自动截断过长的内容（超过50000字符）
4. **超时设置**: 默认30秒超时，可根据需要调整
5. **并发处理**: 支持异步操作，适合批量处理
6. **智能等待**: 自动检测页面加载状态，避免不必要的等待时间

## 注意事项

1. **反爬虫处理**: 工具使用标准的User-Agent，对于有严格反爬虫的网站可能需要额外配置
2. **动态内容**: 某些复杂的SPA应用可能需要更长的等待时间，Playwright会自动处理大部分动态加载内容
3. **内容质量**: 工具会智能判断内容质量，如果静态内容不足会自动尝试动态抓取
4. **API限制**: AI总结功能需要有效的API配置和足够的配额

## 示例输出

```
Python官网是一个提供Python编程语言相关资源的官方网站。网站包含以下主要内容：

1. 下载区域：提供Python最新版本的下载链接
2. 文档中心：包含Python官方文档、教程和API参考
3. 社区信息：展示Python用户成功案例和即将举行的活动
4. 基金会信息：介绍Python软件基金会及其使命

网站设计简洁明了，主要面向Python开发者和学习者，提供从入门到高级的完整学习资源。 