## 具体要求

1. **分析所有开发者分支**
   - 获取所有开发者分支列表
   - 获取每个分支的最新commit信息
   
2. **识别新添加的任务**
   - 比较最新commit与上一次commit的差异
   - 识别在tasks目录下新增的任务文件夹
   
3. **检查实现状态**
   - 完整结构标准：
     - 有docs/目录且包含task.md
     - 有evaluation/目录且包含main.py
     - 有task_config.json文件
   - 状态判定：
     - implemented: 符合完整结构标准
     - implementing: 不符合完整结构标准
     
4. **更新Notion页面**
   - 更新task_tracker_prompt页面：添加新任务的描述信息
   - 更新task_tracker_implementation页面：添加任务实现状态

5. **更新finalpool**
   - 将所有implemented状态的任务添加到task_tracker_finalpool中

## 使用的MCP服务器
- GitHub Server: 用于获取分支和commit信息
- Notion Server: 用于更新Notion页面

## 输出要求
- 生成任务发现报告
- 更新Notion页面的确认信息  
- finalpool更新状态报告