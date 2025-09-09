# Canvas Management Tools

## Overview

这个目录包含了完整的 Canvas LMS 管理工具集

## 工具列表

### 1. Assignment Manager (`assignment_manager.py`)
**功能**: 全面的作业管理工具
- ✅ 从 Markdown 文件创建作业
- ✅ 批量作业创建
- ✅ 作业发布管理
- ✅ 向学生发送私信
- ✅ 获取对话历史记录

**使用方法**:
```bash
# 作为模块运行
python -m utils.app_specific.canvas.tools.assignment_manager --course-id 59 --create-assignments --md-dir assignments/

# 直接运行（需要在项目根目录）
python utils/app_specific/canvas/tools/assignment_manager.py --course-id 59 --message-students --subject "Welcome" --body "欢迎加入课程！"
```

### 2. Course Manager (`course_manager.py`)
**功能**: 综合课程管理工具
- ✅ 创建课程
- ✅ 列出所有课程
- ✅ 删除/结束课程
- ✅ 发布/取消发布课程
- ✅ 获取课程详细信息

**使用方法**:
```bash
# 列出所有课程
python -m utils.app_specific.canvas.tools.course_manager --list-courses

# 创建新课程
python -m utils.app_specific.canvas.tools.course_manager --create-course --name "新课程" --code "NEW101" --publish
```

### 3. Course Initializer (`initialize_course.py`)
**功能**: 快速课程初始化工具
- ✅ 一键创建完整课程
- ✅ 自动添加教师
- ✅ 批量注册学生
- ✅ 课程发布

**使用方法**:
```bash
# 创建课程并添加前5个学生
python -m utils.app_specific.canvas.tools.initialize_course --name "Python编程" --code "PY101" --csv student_list.csv --limit 5
```

### 4. Course Cleanup (`delete_all_courses_auto.py`)
**功能**: 批量删除课程工具
- ✅ 自动删除所有课程
- ✅ 支持自定义URL和Token
- ✅ 详细的删除统计

**使用方法**:
```bash
# 删除所有课程（谨慎使用！）
python -m utils.app_specific.canvas.tools.delete_all_courses_auto --url http://localhost:10001 --token mcpcanvasadmintoken1
```

## 编程接口使用

### 导入工具模块

```python
# 导入主要的工具函数
from utils.app_specific.canvas.tools import (
    assignment_manager_main,
    course_manager_main,
    initialize_course_main,
    delete_all_courses
)

# 直接使用 Canvas API
from utils.app_specific.canvas import CanvasAPI, CourseInitializer

# 初始化 API
canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
initializer = CourseInitializer(canvas)

# 快速创建课程
course = initializer.initialize_course(
    course_name="测试课程",
    course_code="TEST001", 
    csv_file_path="students.csv",
    student_limit=5
)
```

### 与 Canvas 任务集成

这些工具现在可以在所有 Canvas 相关任务中使用：

```python
# 在任何 Canvas 任务中
from utils.app_specific.canvas import CanvasAPI, tools

# 使用工具
canvas = CanvasAPI(url, token)
# 可以直接使用所有功能，不需要本地副本
```

## 配置

所有工具都支持以下配置方式：

1. **命令行参数**: `--url` 和 `--token`
2. **默认值**: `http://localhost:10001` 和 `mcpcanvasadmintoken1`
3. **配置文件**: 从 `token_key_session.py` 自动读取（向后兼容）

## 与原始任务的兼容性

原始的 `canvas-notification-python` 任务中的文件现在都使用 utils 模块：

```python
# 原来的导入方式（已更新为 fallback）
from utils.app_specific.canvas import CanvasAPI
# 如果 utils 不可用，会fallback到本地 canvas_api.py
```

## 优势

### 1. **代码重用**
- 所有 Canvas 任务共享同一套工具
- 减少重复代码
- 统一的 API 接口

### 2. **维护性**
- 单一源代码管理
- 更容易添加新功能
- 集中的bug修复

### 3. **扩展性**
- 可以轻松添加新工具
- 支持多种使用模式
- 模块化设计

### 4. **向后兼容**
- 现有任务无需修改即可使用
- Fallback 机制保证稳定性
- 渐进式迁移支持

## 使用建议

1. **新任务**: 直接从 `utils.app_specific.canvas` 导入
2. **现有任务**: 已自动更新为使用 utils 模块，保持 fallback
3. **命令行使用**: 推荐使用 `-m` 参数运行模块
4. **开发**: 在 utils 中添加新功能，所有任务都能受益

## 注意事项

- ⚠️ **删除工具**: `delete_all_courses_auto.py` 会删除所有课程，使用时请谨慎
- 🔧 **权限**: 确保使用的token有足够权限执行相关操作
- 📁 **路径**: 运行工具时注意当前工作目录和文件路径
- 🔗 **连接**: 确保 Canvas 服务器正在运行并可访问