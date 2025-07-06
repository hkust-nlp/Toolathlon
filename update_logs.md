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
    - 可用工具 "ai_webpage_summary"，"sleep"，"done"

## 2025.7.2 14:00
- 更新canvas mcp server相关说明，见 `install_records/canvas.md`

## 2025.7.2 12:00
- 更新canvas mcp server 版本
- 添加canvas token， 对应使用谷歌账号 kewincpt93@gmail.com 直接授权登录

## 2025.7.5 17:00
- 添加上下文管理工具，已初步验证
- 添加历史记录搜索工具，还未验证，仍需debug

## 2025.7.6 17:00
- 添加历史记录搜索工具，已初步验证