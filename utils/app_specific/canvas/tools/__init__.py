"""
Canvas Management Tools

This package contains command-line tools for managing Canvas LMS instances:
- assignment_manager.py: Create and manage assignments, send messages to students
- course_manager.py: Create, list, delete, and manage courses  
- initialize_course.py: Quick course initialization with student enrollment
- delete_all_courses_auto.py: Bulk course deletion utility

All tools can be run as standalone scripts or imported as modules.
"""

# The tools are designed as command-line scripts, but main functions can be imported
from .assignment_manager import main as assignment_manager_main
from .course_manager import main as course_manager_main, confirm_deletion
from .initialize_course import main as initialize_course_main
from .delete_all_courses_auto import delete_all_courses

__all__ = [
    'assignment_manager_main',
    'course_manager_main', 
    'confirm_deletion',
    'initialize_course_main',
    'delete_all_courses'
]