### 2025.9.6 16:30
- 增强demo.py功能，添加了模型配置命令行参数(model_short_name, provider, max_steps_under_single_turn_mode)
- 改进日志输出格式，使用彩色日志显示重要信息和状态
- 优化容器化执行脚本，完善参数传递和路径处理
- 添加并行执行支持和容器管理功能
- 增强任务配置系统，支持灵活的路径处理和dump设置
- 改进调试和评估工作流程
- 更新各种工具函数和配置
- 添加测试并行任务相关的gitignore条目
- 创建大量测试任务副本用于并行测试

### 2025.9.5 17:3
- 基本完善了基于容器的任务执行隔离
- 相关文件：`scripts/run_single_containerized.sh`

### 2025.9.4 22:30
- 修改了新的web_search工具
- 依赖serper api驱动，替换了原来的基于发请求的工具
- 初步添加了任务级别的镜像支持，每个任务现在在各自容器内运行

### 2025.9.3 21:00
- 追加了github的例子
- 使用了更新的github mcp server

### 2025.9.2 17:35
- 追加了notion的例子
- 使用了更新的notion mcp server

### 2025.8.30 23:00
- 使用新的12306 mcp
- 继续记录整个安装流程及测试脚本

### 2025.8.26 11:30
- 增加对MCP工具超长的管理（只保留前20000字符）
    - 相关文件 `utils/openai_agents_monkey_patch/custom_mcp_util.py`
    - 通过 `BENCH_ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT`  系统变量设置是否启用
- 增加对超长工具输出的搜索和翻页浏览
    - 相关文件 `utils/aux_tools/overlong_tool_manager.py`
    - 启用超长管理时，请务必一并启用该工具


### 2025.8.26 3:30
- 修正轮数统计逻辑

### 2025.8.24 21:30
- 开始创建global preparation脚本, 见 `global_preparation`文件夹
    - 大体目标：
        - 环境配置
        - 所需应用容器部署
        - 其他启动项 （TBD）
            - 配置google calendar和gmail相关
            - 启动所需github repo/google drive folder并得到对应token和folderid
            - and more ...
        

### 2025.8.21 2:20
- 修复canvas mcp的bug
    - 需重新安装 (rm -rf node_modules && npm install)

### 2025.8.20 21:40
- 添加google-forms
    - 相关文件`configs/mcp_servers/google_forms.yaml`

### 2025.8.19 23:20
- 升级emails-mcp-server
    - 0.1.5 -> 0.1.6

### 2025.8.19 22:35
- 升级emails-mcp-server
    - 0.1.0 -> 0.1.5

### 2025.8.19 3:20
- 修改terminal mcp server
    - 添加代理控制，修>>bug以及输出长度控制
    - 需重新安装
    - 相关文件 `configs/mcp_servers/terminal.yaml`

### 2025.8.19 2:20
- 修改yahoo finance mcp server
    - 新增按天搜索价格信息
    - 需重新安装

### 2025.8.18 23:45
- 修改ytb mcp server安装方式
    - fork出新的到个人账户，然后进行源码修改
    - 需重新安装

### 2025.8.15 23:00
- 修改ytb mcp server安装方式及mcp配置方式
    - 可能需要删掉原来local_servers/youtube-mcp-server然后重装一下

### 2025.8.12 18:15
- 修改模拟用户为gpt-5

### 2025.8.11 21:00
- 新增了两个 MCP 服务器的安装命令:
  - `mcp-snowflake-server`: 用于 Snowflake 数据库连接
  - `mcp-scholarly`: 用于学术搜索功能  
- 简化了安装流程，将这两个服务器从源码构建改为直接通过 uv tool 安装
- 更新了 TODOs 列表，移除了已完成的配置项

## 2025.8.11 17:50
- 更新支持模型
    - gpt4.1不再支持，改用gpt-5, 追加了相应修改
    - claude4 opus ->claude4.1 opus
    - 见 `utils/api_model/model_provider.py`

## 2025.8.11 03:30
- 更新账户信息和服务配置
    - 添加Snowflake账户信息到 `accounts.md`
    - 完善本地账户说明，包含poste、canvas、woocommerce管理员账户信息
    - 更新pdf-tools配置，添加临时文件目录配置 `configs/mcp_servers/pdf-tools.yaml`
    - 添加Snowflake配置到 `configs/token_key_session.py`
    - 更新用户数据文件 `configs/users_data.json`
    - 新增Snowflake MCP服务器配置 `configs/mcp_servers/snowflake.yaml`
    - 添加csv格式用户数据文件 `configs/users_data.csv`
    - 新增端口监控工具 `utils/general/port_monitor.py`
    - 优化Canvas用户创建脚本和Woocommerce部署脚本

## 2025.8.9 23:50
- 添加canvas admin账户信息
    - 相关文件 `deployment/canvas/README.md`

## 2025.8.7 16:25
- 清理调试文件
    - 删除 `debug.json` 文件
    - 更新 `.gitignore`，添加 `debug.json` 和 `debug.jsonl` 忽略规则

## 2025.8.7 16:21
- 完成邮件MCP配置全局共享
    - 添加全局邮件配置文件 `configs/global_emails.json`
    - 添加邮件MCP服务配置 `configs/mcp_servers/emails.yaml`
    - 更新token配置，支持邮件服务 `configs/token_key_session.py`
    - 新增用户数据文件 `configs/users_data.csv`, `configs/users_data.json`, `configs/sers_data.csv`
    - 移动google_search配置到legacy目录 `configs/legacy_servers/google_search.yaml`
- 修正woocommerce服务端口号从10002到10003
- 添加账户信息说明文档 `accounts.md`

## 2025.8.7 14：30
- 更新安装指南，指定各uv tool安装版本
    - 相关文件 `installation_guide.md`

## 2025.8.4 21:30
- 完成poste邮件服务部署脚本
    - 一键运行 `bash deployment/poste/scripts/setup.sh` 即可
    - 会在http://localhost:10005监听
    - 自动创建100个邮箱账户，方便进行邮件相关的测试和操作
    - 账户信息保存在 `deployment/poste/configs/created_accounts.json` 中
- 更新deployment目录的.gitignore规则
    - 改进忽略规则，只保留scripts文件夹和utils文件夹
    - 便于新建deployment子目录时自动包含scripts文件夹

## 2025.8.1 16:30
- 添加Google Cloud MCP服务器支持
    - 新增 `configs/mcp_servers/google-cloud.yaml` 配置文件
    - 新增 `configs/mcp-bench0606-2b68b5487343.json` Google Cloud服务账户凭证文件
    - 更新 `configs/token_key_session.py`，添加Google Cloud相关配置项
        - 添加gcp_project_id、gcp_service_account_path等配置
        - 支持Google Cloud Storage、BigQuery、Logging、Compute Engine等服务
    - 我们使用任务特定的allow_xx来进行任务之间的隔离
        - 见 `tasks/debug/debug-task/token_key_session.py`， 会覆盖原有的空全局allow_xx
- 更新任务配置结构
    - 相关文件 `utils/data_structures/task_config.py`

## 2025.7.30 16:30
- 删除原playwright.yaml配置文件，移至legacy_servers目录
    - 删除 `configs/mcp_servers/playwright.yaml`
    - 新增 `configs/legacy_servers/playwright.yaml`
    - 新增 `configs/mcp_servers/playwright_with_chunk.yaml` 配置文件，支持分块处理
- 删除ui_tars_browser.yaml配置文件
    - 删除 `configs/mcp_servers/ui_tars_browser.yaml`
- 更新调试配置文件
    - 相关文件 `debug.json`
- 更新依赖包
    - 相关文件 `package.json`, `package-lock.json`
- 更新评估调试配置
    - 相关文件 `scripts/debug_eval_config.json`
- 更新模型提供器和辅助工具
    - 相关文件 `utils/api_model/model_provider.py`, `utils/general/helper.py`

## 2025.7.29 15:30
- 完成canvas服务部署脚本
    - 一键运行 `bash deployment/canvas/scripts/setup.sh start` 即可
    - 会在http://localhost:10001 https://localhost:20001监听
    - 自动生成200个账户，可之后构建自动化脚本使用这些账户进行课程设置等操作构建初始状态
    - 账户信息保存在 `deployment/canvas/configs/canvas_users.json` 中
- 完成woocommerce服务部署脚本
    - 一键运行 `deployment/woocommerce/scripts/setup.sh` 即可
    - 会在http://localhost:10003监听
    - 完全停止请使用 `podman pod stop woo-pod && podman pod rm -f woo-pod"
    - 会自动生成20个子站点，形成20个相互隔离的店铺方便操作，，可之后构建自动化脚本使用这些账户进行店铺设置等操作构建初始状态
    - 账户信息保存在 `deployment/woocommerce/configs/multisite-api-keys.json` 中
- 完成k8s集群部署脚本
    - 一键运行 `deployment/k8s/scripts/setup.sh` 即可
        - TODO: 创建和任务对应的k8sconfigfile
    - 完成部署后，config会保存在deployment/k8s/configs
- 添加woocommerce mcp
    - 相关文件 `configs/mcp_servers/woocommerce.yaml`
    - 由于每个任务操作的店铺不同，需要在任务下overwrite所需的api， 如`tasks/debug/debug-task/token_key_session.py`
- 添加k8s mcp
    - 相关文件 `configs/mcp_servers/k8s.yaml`
    - 由于每个任务操作的集群不同，需要在任务下overwrite所需的k8sconfig， 如`tasks/debug/debug-task/token_key_session.py`


## 2025.7.27 23:59
- 添加notion服务器
    - 相关文件 configs/mcp_servers/notion.yaml

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