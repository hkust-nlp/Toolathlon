## 2025.7.25 18:40
- 添加canvas为自行部署，测试进行中
    
## 2025.7.23 13:40
- 优化上下文管理和历史记录显示功能
    - 改进历史记录概览的格式化显示，支持多行内容和更好的截断处理
    - 优化工具调用和工具结果的显示格式，增加更多细节信息
    - 修正上下文重置逻辑，保留轮数累积信息和截断历史
    - 相关文件 `utils/roles/context_managed_runner.py`, `utils/roles/task_agent.py`
- 更新依赖包版本
    - 升级 `@eslint/plugin-kit` 到 0.3.4
    - 升级 `form-data` 到 4.0.4
    - 相关文件 `package-lock.json`

## 2025.7.23 0:02
- 修改语言模式参数命名
    - 将 `--en_mode` 参数改为 `--cn_mode`，默认为英文模式，启用参数后为中文模式
    - 对应的文件后缀从 `_en` 改为 `_cn`
    - 相关文件 `demo.py`, `utils/data_structures/task_config.py`

## 2025.7.22 23:59
- 添加YouTube字幕MCP服务器支持
    - 修复原有youtube服务器字幕功能问题
    - 相关文件 `configs/mcp_servers/youtube_transcript.yaml`
- 升级Excel MCP服务器版本至0.1.4
    - 相关文件 `pyproject.toml`
- 增强上下文过长错误处理机制
    - 在模型提供器中添加ContextTooLongError异常类，用于检测和处理上下文超长错误
    - 上下文超长时自动清空上下文并提供最近十轮历史上下文重新开始
    - 相关文件 `utils/api_model/model_provider.py`, `utils/roles/context_managed_runner.py`
- 大幅扩展和增强历史记录工具功能
    - 添加正则表达式搜索支持 (`search_history` 工具新增 `use_regex` 参数)
    - 添加轮内搜索功能 (`search_in_turn` 新工具)
    - 增强查看历史轮次功能，支持内容截断 (`view_history_turn` 工具新增 `truncate` 参数)
    - 优化浏览历史功能，支持内容截断 (`browse_history` 工具新增 `truncate` 参数)
    - 改进搜索结果上下文显示和匹配高亮
    - 相关文件 `utils/aux_tools/history_manager.py`, `utils/aux_tools/history_tools.py`
- 更新调试任务配置
    - 修改所需MCP服务器为excel和filesystem
    - 相关文件 `tasks/debug/debug-task/task_config.json`
- 更新.gitignore规则
    - 重新启用debug脚本忽略规则
    - 添加debug任务文件夹忽略规则

## 2025.7.21 4:30
- 添加网页搜索工具 web_search，支持在任务中进行网页搜索
    - 相关文件 `utils/aux_tools/web_search.py`, `utils/roles/task_agent.py`
    - 可用工具 "web_search"

## 2025.7.18 11:00
- 添加自定义 pdf_tools_mcp server, 移除原有的pdf相关server

## 2025.7.17 17:00
- 移除pdf_tools，其功能实现有bug，用处也不是很大，可以被直接写python脚本覆盖

## 2025.7.15 15:00
- 添加user_agent到playwright，为python executor添加超时限制

## 2025.7.15 14:00
- 修正terminal服务器的使用方法, 请先 `uv tool install cli-mcp-server`

## 2025.7.15 11:00
- 增加了英文模式，在原任务下添加带_en后缀各种脚本和文件夹即可识别，demo.py增加参数 --en_mode

## 2025.7.12 18:00
- 移除了code_runner server (因为没法指定工作路径，感觉有点笨)，改用一个新写的python执行工具.
    - 可用工具 "python_execute"

## 2025.7.8 14:00
- 修改安装问题，改用uv sync

## 2025.7.8 11:00
- 修改google sheet mcp server认证方式为OAuth 2.0， 所有功能均正常
    - 相关文件： `configs/mcp_servers/google_sheet.yaml`

## 2025.7.7 17:00
- 添加mcp pdf tools
    - 相关文件： `install_records/pdf_tools.md`, `configs/mcp_servers/pdf_tools.yaml`

## 2025.7.7 11:50
- 修复任务override token_key_session 路径不存在的bug

## 2025.7.7 11:10
- 支持任务override token_key_session
    - 相关文件 `tasks/debug/debug-task/token_key_session.py` 在这里填入和 `configs/token_key_session.py` 同名的变量可以覆盖后者的设置
    - TODO: gmail/google calendar现在依赖于.gmail-mcp 和 .calendar-mcp， 想想办法

## 2025.7.7 3:45
- 添加google sheet mcp server
    - 相关文件 `configs/google_sheets_service_credentials.json` `configs/mcp_servers/google_sheet.yaml`
    - *有点小问题，尝试创建spreadsheet时报403权限错误

## 2025.7.7 3:00
- 恢复高德地图mcp
    - 相关文件 `configs/mcp_servers/amap.yaml`

## 2025.7.6 17:30
- 修改log保存逻辑
    - 相关文件 `utils/roles/task_agent.py`

## 2025.7.6 17:20
- 修改log保存逻辑
    - 相关文件 `utils/roles/task_agent.py`

## 2025.7.6 17:00
- 添加历史记录搜索工具，已初步验证
    - 相关文件 `utils/roles/context_managed_runner.py`, `utils/roles/task_agent.py`, `utils/aux_tools/history_manager.py`, `utils/aux_tools/history_tools.py`
    - 可用工具 "history"

## 2025.7.5 17:00
- 添加上下文管理工具，已初步验证
    - 相关文件 `utils/roles/context_managed_runner.py`, `utils/roles/task_agent.py`, `utils/aux_tools/context_management_tools.py`
    - 可用工具 "manage_context"
- 添加历史记录搜索工具，还未验证，仍需debug

## 2025.7.2 18:30
- 修改gemini模型名称，以及添加各模型上下文限制
    - 相关文件 `utils/api_model/model_provider.py`

## 2025.7.2 17:30
- 根据cursor的system prompt设计第一版general prompt
    - 相关文件 `utils/system_prompts/general_v0.txt`

## 2025.7.2 16:30
- 添加本地AI总结网页工具 (4.1-nano 驱动)
    - 相关文件  `utils/aux_tools/ai_webpage_summary.py`
- 添加本地工具到task_config中
    - 在task config中添加 "needed_local_tools": ["ai_webpage_summary"] 即可
    - 可用工具 "ai_webpage_summary"，"sleep"，"claim_done"

## 2025.7.2 14:00
- 更新canvas mcp server相关说明，见 `install_records/canvas.md`

## 2025.7.2 12:00
- 更新canvas mcp server 版本
- 添加canvas token， 对应使用谷歌账号 kewincpt93@gmail.com 直接授权登录