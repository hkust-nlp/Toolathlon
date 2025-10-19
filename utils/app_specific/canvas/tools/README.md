# Canvas Management Tools

## Overview

This directory contains a comprehensive set of tools for managing Canvas LMS.

## Tool List

### 1. Assignment Manager (`assignment_manager.py`)
**Features:** Comprehensive assignment management
- ✅ Create assignments from Markdown files
- ✅ Bulk assignment creation
- ✅ Manage assignment publishing
- ✅ Send private messages to students
- ✅ Retrieve conversation history

**Usage:**
```bash
# Run as a module
python -m utils.app_specific.canvas.tools.assignment_manager --course-id 59 --create-assignments --md-dir assignments/

# Run directly (must be run from the project root)
python utils/app_specific/canvas/tools/assignment_manager.py --course-id 59 --message-students --subject "Welcome" --body "Welcome to the course!"
```

### 2. Course Manager (`course_manager.py`)
**Features:** Comprehensive course management
- ✅ Create new courses
- ✅ List all courses
- ✅ Delete/end courses
- ✅ Publish/unpublish courses
- ✅ Retrieve course details

**Usage:**
```bash
# List all courses
python -m utils.app_specific.canvas.tools.course_manager --list-courses

# Create a new course
python -m utils.app_specific.canvas.tools.course_manager --create-course --name "New Course" --code "NEW101" --publish
```

### 3. Course Initializer (`initialize_course.py`)
**Features:** Rapid course initialization
- ✅ One-click full course creation
- ✅ Auto-add teachers
- ✅ Bulk student registration
- ✅ Publish course

**Usage:**
```bash
# Create a course and add the first 5 students from CSV
python -m utils.app_specific.canvas.tools.initialize_course --name "Python Programming" --code "PY101" --csv student_list.csv --limit 5
```

### 4. Course Cleanup (`delete_all_courses_auto.py`)
**Features:** Bulk course deletion
- ✅ Automatically delete all courses
- ✅ Support for custom URL and token
- ✅ Detailed deletion statistics

**Usage:**
```bash
# Delete all courses (use with caution!)
python -m utils.app_specific.canvas.tools.delete_all_courses_auto --url http://localhost:10001 --token mcpcanvasadmintoken1
```

## Programming API Usage

### Importing Tool Modules

```python
# Import main tool functions
from utils.app_specific.canvas.tools import (
    assignment_manager_main,
    course_manager_main,
    initialize_course_main,
    delete_all_courses
)

# Use Canvas API directly
from utils.app_specific.canvas import CanvasAPI, CourseInitializer

# Initialize the API
canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
initializer = CourseInitializer(canvas)

# Quickly create a course
course = initializer.initialize_course(
    course_name="Test Course",
    course_code="TEST001", 
    csv_file_path="students.csv",
    student_limit=5
)
```

### Integration with Canvas Tasks

These tools can now be used in all Canvas-related tasks:

```python
# In any Canvas-related task
from utils.app_specific.canvas import CanvasAPI, tools

# Use tools
canvas = CanvasAPI(url, token)
# All features are available without local copies
```

## Configuration

All tools support the following configuration methods:

1. **Command-line arguments**: `--url` and `--token`
2. **Default values**: `http://localhost:10001` and `mcpcanvasadmintoken1`
3. **Config file**: Automatically reads from `token_key_session.py` (for backward compatibility)

## Backward Compatibility

Files from the original `canvas-notification-python` tasks now use the utils module:

```python
# Previous import method (now updated with fallback support)
from utils.app_specific.canvas import CanvasAPI
# If the utils module is unavailable, local canvas_api.py will be used as fallback
```

## Advantages

### 1. **Code Reuse**
- All Canvas tasks share the same toolset
- Less code duplication
- Unified API interface

### 2. **Maintainability**
- Single source code management
- Easier to add new features
- Centralized bug fixes

### 3. **Extensibility**
- Easily add new tools
- Supports multiple usage modes
- Modular design

### 4. **Backward Compatibility**
- Existing tasks can use the new modules without modification
- Fallback mechanism ensures stability
- Supports gradual migration

## Recommendations

1. **New tasks:** Import directly from `utils.app_specific.canvas`
2. **Existing tasks:** Already updated to use the utils module with fallback
3. **Command-line usage:** Recommended to run modules with the `-m` flag
4. **Development:** Add new features directly in utils for all tasks to benefit

## Notes

- ⚠️ **Deletion tool:** `delete_all_courses_auto.py` will delete all courses; use with caution
- 🔧 **Permissions:** Ensure your token has sufficient permissions
- 📁 **Paths:** Pay attention to current working directory and file paths when running tools
- 🔗 **Connection:** Make sure the Canvas server is running and reachable