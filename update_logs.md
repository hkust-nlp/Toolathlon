## 2025.7.2 12:00
- 更新canvas mcp server 版本
- 添加canvas token， 对应使用谷歌账号 kewincpt93@gmail.com 直接授权登录

## 2025.7.2 14:00
- 更新canvas mcp server相关说明，见 `install_records/canvas.md`

## 2025.7.2 16:30
- 添加本地AI总结网页工具 (4.1-nano 驱动)
    - 相关文件  `utils/aux_tools/ai_webpage_summary.py`
- 添加本地工具到task_config中
    - 在task config中添加 "needed_local_tools": ["ai_webpage_summary"] 即可
    - 可用工具 "ai_webpage_summary"，"sleep"，"done"

## 2025.7.2 17:30
- 根据cursor的system prompt设计第一版general prompt
    - 相关文件 `utils/system_prompts/general_v0.txt`

