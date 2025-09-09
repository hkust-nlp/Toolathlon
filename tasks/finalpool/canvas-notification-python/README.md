# Canvas REST API 管理工具

这个工具集提供了完整的Canvas LMS管理功能，使用Canvas REST API来创建课程、管理用户和发布课程。

## 文件说明

### 核心文件
- **`canvas_api.py`** - 核心Canvas API库，包含所有基础功能
- **`initialize_course.py`** - 快速课程初始化脚本
- **`publish_course.py`** - 课程发布工具（原始版本）
- **`examples.py`** - 使用示例和演示代码
- **`preprocess/main.py`** - 任务预处理管道，自动创建"Introduction to AI"课程

### 配置文件
- **`token_key_session.py`** - Canvas API配置文件（URL和访问令牌）

### 数据文件
- **`initial_workspace/student_list.csv`** - 学生数据文件（格式：Name, email）
- **`preprocess/student_list.csv`** - 预处理任务专用学生数据文件
- **`preprocess/assignments/`** - 作业markdown文件目录

## 主要功能

### CanvasAPI 类功能
- ✅ 创建课程 (`create_course`)
- ✅ 发布/取消发布课程 (`publish_course`, `unpublish_course`)
- ✅ 删除课程 (`delete_course`)
- ✅ 创建用户 (`create_user`)
- ✅ 查找用户 (`find_user_by_email`)
- ✅ 自动获取或创建用户 (`get_or_create_user`)
- ✅ 用户注册课程 (`enroll_user`)
- ✅ 批量注册学生 (`batch_enroll_students`)
- ✅ 从CSV加载学生数据 (`load_students_from_csv`)
- ✅ 添加教师到课程 (`add_teacher_to_course`)
- ✅ 创建作业 (`create_assignment`, `create_assignment_from_md`)
- ✅ 批量创建作业 (`batch_create_assignments_from_md`)
- ✅ 发送私信 (`send_message_to_student_by_email`)
- ✅ 批量发送消息 (`batch_message_students`)

### CourseInitializer 类功能
- ✅ 一键初始化完整课程 (`initialize_course`)
- ✅ 自动创建课程、添加教师、注册学生、发布课程

### Canvas预处理管道 (CanvasPreprocessPipeline)
- ✅ 自动创建"Introduction to AI"课程
- ✅ 从CSV选择特定位置学生（1st, 3rd, 5th, 10th, 15th）进行注册
- ✅ 从markdown文件批量创建作业（homework1, homework2, project1）
- ✅ 添加当前用户为教师
- ✅ 发布课程使其可用
- ✅ 集成配置文件管理

## 使用方法

### 🚀 Canvas预处理管道（推荐）

运行预处理管道自动创建"Introduction to AI"课程：

```bash
# 运行预处理管道
cd preprocess/
python3 main.py

# 使用自定义工作区（可选）
python3 main.py --agent_workspace /path/to/workspace
```

预处理管道会自动执行以下步骤：
1. 创建"Introduction to AI"课程 (AI101)
2. 添加当前用户为教师
3. 从CSV选择特定学生进行注册（位置1,3,5,10,15）
4. 从assignments/目录创建作业（homework1.md, homework2.md, project1.md）
5. 发布课程

**选择的学生（基于preprocess/student_list.csv）：**
- 位置1: Stephanie Cox (stephanie.cox@mcp.com)
- 位置3: Gary Collins (gary_collins@mcp.com)  
- 位置5: Stephanie Gonzalez (sgonzalez3@mcp.com)
- 位置10: Raymond Cox (raymond_cox@mcp.com)
- 位置15: Tracy Stewart (stewartt@mcp.com)

### 2. 快速初始化课程

```bash
# 基础使用 - 创建课程并添加前5个学生
python3 initialize_course.py --name "Python编程" --code "PY101" --csv initial_workspace/student_list.csv --limit 5

# 完整参数示例
python3 initialize_course.py \
  --name "机器学习基础" \
  --code "ML101" \
  --csv initial_workspace/student_list.csv \
  --limit 8 \
  --syllabus "机器学习概念和应用介绍" \
  --start-date "2025-09-01T00:00:00Z" \
  --end-date "2025-12-31T23:59:59Z"

# 不发布课程（仅创建）
python3 initialize_course.py --name "测试课程" --code "TEST" --csv initial_workspace/student_list.csv --no-publish

# 不添加自己为教师
python3 initialize_course.py --name "学生课程" --code "STU001" --csv initial_workspace/student_list.csv --no-teacher
```

### 3. 运行默认演示

```bash
# 无参数运行，使用默认配置创建演示课程
python3 initialize_course.py
```

### 4. 编程方式使用

```python
from utils.app_specific.canvas import CanvasAPI, CourseInitializer

# 初始化API
canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")

# 方法1：手动步骤
course = canvas.create_course("高级Python", "PY301")
canvas.add_teacher_to_course(course['id'], 139)  # 添加教师
students = canvas.load_students_from_csv("student_list.csv", limit=5)
canvas.batch_enroll_students(course['id'], students)
canvas.publish_course(course['id'])

# 方法2：一键初始化
initializer = CourseInitializer(canvas)
course = initializer.initialize_course(
    course_name="数据科学入门",
    course_code="DS101", 
    csv_file_path="student_list.csv",
    student_limit=10
)
```

### 5. 运行示例代码

```bash
python3 examples.py
```

然后选择要运行的示例：
- 1: 基础课程创建
- 2: 快速课程初始化  
- 3: 批量课程创建
- 4: 课程管理操作
- 5: 用户管理
- 0: 运行所有示例

## 参数说明

### initialize_course.py 参数

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--name, -n` | ✅ | - | 课程名称 |
| `--code, -c` | ✅ | - | 课程代码 |
| `--csv` | ✅ | - | 学生CSV文件路径 |
| `--limit, -l` | ❌ | 全部 | 最大学生数量 |
| `--url` | ❌ | http://localhost:10001 | Canvas服务器地址 |
| `--token` | ❌ | mcpcanvasadmintoken1 | Canvas访问令牌 |
| `--account-id` | ❌ | 1 | Canvas账户ID |
| `--no-publish` | ❌ | False | 不发布课程 |
| `--no-teacher` | ❌ | False | 不添加当前用户为教师 |
| `--syllabus` | ❌ | - | 课程大纲内容 |
| `--start-date` | ❌ | - | 课程开始时间 |
| `--end-date` | ❌ | - | 课程结束时间 |

## CSV文件格式

学生CSV文件必须包含以下列：

```csv
Name,email
张三,zhangsan@example.com
李四,lisi@example.com
王五,wangwu@example.com
```

## 配置说明

### Canvas 连接配置

配置文件 `token_key_session.py` 包含：
- **服务器地址**: `localhost:10001`
- **访问令牌**: `mcpcanvasadmintoken1`

```python
# token_key_session.py
from addict import Dict

all_token_key_session = Dict(
    canvas_api_token = "mcpcanvasadmintoken1",
    canvas_domain = "localhost:10001",
)
```

### 自定义配置
- 预处理管道自动从 `token_key_session.py` 读取配置
- 可以通过命令行参数或直接修改脚本中的配置来更改Canvas连接设置
- 其他脚本也可通过命令行参数覆盖默认配置

## 功能特点

✨ **自动化** - 一键完成课程创建到发布的全流程
✨ **灵活** - 支持自定义课程参数和学生数量限制  
✨ **智能** - 自动检测现有用户，避免重复创建
✨ **批量** - 支持批量操作和错误处理
✨ **发布** - 解决Canvas MCP无法发布课程的问题
✨ **易用** - 命令行界面和编程接口双重支持

## 测试结果

✅ 已成功测试：
- 课程创建和发布
- 学生批量注册  
- 教师添加
- CSV文件解析
- 错误处理
- 参数验证

## 🆕 新增功能详解

### 作业管理功能

#### assignment_manager.py 使用方法

```bash
# 创建示例作业并发布
python3 assignment_manager.py --course-id 59 --create-samples --create-assignments

# 从指定目录创建作业
python3 assignment_manager.py --course-id 59 --md-dir my_assignments/ --create-assignments --points 50

# 列出课程中的所有作业
python3 assignment_manager.py --course-id 59 --list-assignments

# 向学生发送私信
python3 assignment_manager.py --course-id 59 --message-students --subject "作业提醒" --body "请及时完成作业"

# 向特定学生发送消息
python3 assignment_manager.py --course-id 59 --message-students --emails "student@mcp.com" --subject "个人通知" --body "个人消息内容"

# 查看与学生的聊天记录
python3 assignment_manager.py --course-id 59 --get-conversations --email "student@mcp.com"
```

#### 编程方式使用作业功能

```python
from utils.app_specific.canvas import CanvasAPI

canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")

# 创建单个作业
assignment = canvas.create_assignment(
    course_id=59,
    name="期末项目", 
    description="完成一个完整的Web应用项目",
    points_possible=200,
    due_at="2025-12-31T23:59:59Z",
    published=True
)

# 从Markdown文件创建作业
assignment = canvas.create_assignment_from_md(
    course_id=59,
    md_file_path="assignments/homework1.md",
    points_possible=100,
    due_days_from_now=7
)

# 批量创建作业
stats = canvas.batch_create_assignments_from_md(
    course_id=59,
    md_directory="assignments/",
    points_possible=100,
    due_days_interval=7,
    published=True
)

# 发布作业
canvas.publish_assignment(course_id=59, assignment_id=1)

# 获取作业列表
assignments = canvas.list_assignments(course_id=59)
```

#### 编程方式使用私信功能

```python
# 向学生发送私信
canvas.send_message_to_student_by_email(
    email="student@mcp.com",
    subject="作业成绩通知",
    body="您的第一次作业成绩将与第二次作业成绩保持一致，请认真完成。",
    course_id=59
)

# 批量发送消息
stats = canvas.batch_message_students(
    student_emails=["student1@mcp.com", "student2@mcp.com"],
    subject="课程通知",
    body="重要课程更新信息",
    course_id=59
)

# 获取与学生的对话记录
user = canvas.find_user_by_email("student@mcp.com")
conversations = canvas.get_conversation_with_user(user['id'])

# 回复对话
canvas.reply_to_conversation(conversation_id=1, body="谢谢您的问题，我会尽快回复。")
```

### Markdown文件格式

作业的Markdown文件可以包含完整的作业描述：

```markdown
# 作业标题

## 目标
描述作业的学习目标

## 要求
1. 具体要求1
2. 具体要求2

## 提交方式
- 文件格式要求
- 提交截止时间

## 评分标准
- 功能完整性: 60%
- 代码质量: 30%
- 文档说明: 10%
```

### 测试脚本

运行综合测试：
```bash
python3 test_new_features.py
```

该脚本会测试所有新功能包括：
- 作业创建和管理
- 从Markdown批量创建作业  
- 私信发送和接收
- 对话记录获取

## 注意事项

1. 确保Canvas服务器正在运行
2. 验证访问令牌有效
3. CSV文件格式正确
4. 网络连接正常
5. 具有相应的Canvas权限
6. Markdown文件路径正确
7. 私信功能需要正确的用户权限

## 错误排查

如果遇到问题：
1. 检查Canvas服务器状态
2. 验证访问令牌
3. 确认CSV文件路径和格式
4. 检查网络连接
5. 查看详细错误信息
6. 验证课程ID是否正确
7. 检查用户权限设置

## 🎯 完整工作流程示例

### 推荐工作流程（使用预处理管道）

```bash
# 1. 运行预处理管道（推荐）
cd preprocess/
python3 main.py

# 这会自动完成：
# - 创建"Introduction to AI"课程
# - 添加教师（当前用户）
# - 注册5个特定学生
# - 创建3个作业（homework1, homework2, project1）
# - 发布课程
```

### 手动工作流程

```bash
# 1. 创建课程并添加学生
python3 initialize_course.py --name "Web开发" --code "WEB101" --csv student_list.csv --limit 10

# 2. 创建作业
python3 assignment_manager.py --course-id 61 --create-samples --create-assignments

# 3. 向学生发送欢迎消息
python3 assignment_manager.py --course-id 61 --message-students --subject "欢迎加入课程" --body "欢迎大家加入Web开发课程！"

# 4. 查看课程作业
python3 assignment_manager.py --course-id 61 --list-assignments
```

## 预处理管道输出示例

```
🎓 Canvas Course Preprocessing - Introduction to AI
Setting up course with specific students and assignments...
📋 Configuration:
   Canvas URL: http://localhost:10001
   Canvas Token: mcpcanvas...en1

🚀 Canvas Course Preprocessing Pipeline
============================================================
Task: Set up 'Introduction to AI' course with specific students and assignments
✅ Connected to Canvas as: Admin User

📚 Loaded 21 total students from CSV
🎯 Selecting students at positions: [1, 3, 5, 10, 15]
   Position 1: Stephanie Cox (stephanie.cox@mcp.com)
   Position 3: Gary Collins (gary_collins@mcp.com)
   Position 5: Stephanie Gonzalez (sgonzalez3@mcp.com)
   Position 10: Raymond Cox (raymond_cox@mcp.com)
   Position 15: Tracy Stewart (stewartt@mcp.com)

🏗️  Step 1: Creating course 'Introduction to AI'
✅ Course created successfully!
   Course ID: 123
   Course URL: http://localhost:10001/courses/123

👨‍🏫 Step 2: Adding teacher to course
✅ Added Admin User as teacher

👥 Step 3: Enrolling 5 target students
✅ All 5 students enrolled successfully!

📝 Step 4: Creating assignments from assignments/
✅ Created 3/3 assignments
📋 Assignments created:
   - Homework 1: Introduction to Python (ID: 456)
   - Homework 2: Data Structures (ID: 457)
   - Project 1: Final Project (ID: 458)

📤 Step 5: Publishing course
✅ Course published successfully!

🎉 Pipeline completed successfully!
📊 Summary:
   Course: Introduction to AI (ID: 123)
   Students enrolled: 5
   Assignments created: 3 (homework1, homework2, project1)
   Course status: Published
   Direct link: http://localhost:10001/courses/123
```