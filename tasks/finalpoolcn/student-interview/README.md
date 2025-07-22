# 学生面试安排任务 (Student Interview Task)

## 任务概述

这是一个基于Gmail和Google Calendar的MCP Agent任务，模拟HKUST教授处理学生面试安排的真实场景。

## 任务描述

作为HKUST的一名教授，您最近收到了5名学生的简历邮件，需要安排面试。由于人数较多，您只想与有独立一作发表的学生进行面试。任务要求：

1. **邮件筛选**：在收件箱中筛选出有独立一作发表的学生简历
2. **日历查看**：查看今天和明天的空余时间
3. **面试安排**：为符合条件的学生安排面试时间
4. **日程同步**：将面试安排同步到Google Calendar
5. **结果报告**：告知具体的面试时间安排

## 学生简历概况

任务中包含5名学生的简历：

| 学生姓名 | 学校 | 独立一作发表 | 筛选结果 |
|---------|------|-------------|----------|
| 张小明 | 清华大学 | ✅ (ICML 2023, NeurIPS 2023) | 应安排面试 |
| 李小红 | 北京大学 | ❌ (无正式发表) | 不安排面试 |
| 王大伟 | 浙江大学 | ✅ (CVPR 2023) | 应安排面试 |
| 刘小丽 | 上海交通大学 | ❌ (仅为第二、三作者) | 不安排面试 |
| 陈小强 | 中山大学 | ✅ (ICML 2023, KDD 2023, AAAI 2023) | 应安排面试 |

## 评估标准

任务的评估基于以下几个维度：

1. **筛选准确性** (50分)：是否正确识别并筛选出3名有独立一作发表的学生
2. **时间安排合理性** (30分)：面试时间是否安排在今天和明天两天内
3. **日程完整性** (20分)：是否为每个合格学生都安排了具体的面试时间

## 目录结构

```
tasks/wenshuo/Student-Interview/
├── docs/
│   ├── task.md                    # 任务描述
│   ├── agent_system_prompt.md     # Agent系统提示
│   └── user_system_prompt.md      # 用户系统提示
├── files/
│   ├── emails.jsonl               # 学生简历邮件数据
│   └── placeholder_values.json    # 占位符配置
├── preprocess/
│   ├── main.py                    # 预处理主程序
│   ├── send_email.py              # 邮件发送工具
│   ├── clean_gmail_calendar.py    # 清理工具
│   └── wait_for_emails.py         # 邮件等待工具
├── evaluation/
│   └── main.py                    # 评估脚本
├── groundtruth_workspace/
│   └── today.txt                  # 基准日期
└── task_config.json               # 任务配置
```

## 使用方法

### 1. 预处理
```bash
# 运行预处理脚本，发送学生简历邮件
python tasks/wenshuo/Student-Interview/preprocess/main.py --credentials_file configs/credentials.json
```

### 2. 运行任务
启动Agent系统，让其处理学生面试安排任务。

### 3. 评估结果
```bash
# 运行评估脚本
python tasks/wenshuo/Student-Interview/evaluation/main.py
```

## 技术要求

- **MCP服务器**：gmail, google_calendar
- **Python依赖**：详见各脚本的导入部分
- **Google账户**：需要配置Gmail和Google Calendar API访问权限

## 预期行为

一个成功的Agent应该能够：

1. 自动读取Gmail中的学生简历邮件
2. 识别并解析每个学生的发表情况
3. 准确筛选出有独立一作发表的学生
4. 查看Google Calendar中的空余时间
5. 合理安排面试时间（避免冲突，分布在今明两天）
6. 将面试安排同步到Google Calendar
7. 向用户报告具体的面试时间安排

## 注意事项

- 任务专注于"独立一作"的识别，需要区分"第一作者"与"第二/三作者"
- 时间安排需要考虑实际的日历冲突
- 每场面试建议安排45分钟到1小时
- 评估脚本会检查Calendar中的实际事件安排 