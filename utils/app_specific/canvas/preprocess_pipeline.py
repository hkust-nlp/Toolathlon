#!/usr/bin/env python3
"""
Canvas Preprocessing Utilities

This module provides utility functions for Canvas LMS preprocessing tasks,
focusing on common operations that can be reused across different tasks.
"""

import csv
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from .api_client import CanvasAPI, CanvasTokenManager


class CanvasPreprocessUtils:
    """Utility functions for Canvas preprocessing operations"""
    
    def __init__(self, canvas_api: CanvasAPI):
        """
        Initialize utils with Canvas API instance
        
        Args:
            canvas_api: Initialized CanvasAPI instance
        """
        self.canvas = canvas_api
    
    def add_user_to_course_by_email(self, course_id: int, user_email: str, 
                                   role: str = 'StudentEnrollment') -> bool:
        """
        Add a user to a course by email address
        
        Args:
            course_id: Course ID
            user_email: User's email address
            role: Enrollment role (StudentEnrollment, TeacherEnrollment, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        # Find the user (don't create, users should already exist)
        user = self.canvas.find_user_by_email(user_email)
        if not user:
            print(f"User not found: {user_email}")
            return False
        
        # Enroll user in course
        enrollment = self.canvas.enroll_user(course_id, user['id'], role)
        if enrollment:
            role_name = "teacher" if role == 'TeacherEnrollment' else "student"
            print(f"Added {user.get('name', user_email)} as {role_name}")
            return True
        else:
            print(f"Failed to add {user_email} to course")
            return False
    
    def batch_enroll_users_from_csv(self, course_id: int, csv_file: Path, 
                                   role: str = 'StudentEnrollment',
                                   name_column: str = 'Name',
                                   email_column: str = 'email',
                                   selected_indices: List[int] = None) -> Dict:
        """
        Enroll users from CSV file
        
        Args:
            course_id: Course ID
            csv_file: Path to CSV file containing user data
            role: Enrollment role for all users
            name_column: Name of the name column in CSV
            email_column: Name of the email column in CSV
            selected_indices: Optional list of 0-based indices to select specific users
            
        Returns:
            Dictionary with enrollment statistics
        """
        if not csv_file.exists():
            print(f"CSV file not found: {csv_file}")
            return {'total': 0, 'successful': 0, 'failed': 0}
        
        stats = {'total': 0, 'successful': 0, 'failed': 0}
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                users_list = list(reader)
                
                # Select specific indices if provided, otherwise use all
                if selected_indices:
                    selected_users = []
                    for index in selected_indices:
                        if 0 <= index < len(users_list):
                            selected_users.append((index, users_list[index]))
                        else:
                            print(f"Index {index} out of range (max: {len(users_list)-1})")
                else:
                    selected_users = list(enumerate(users_list))
                
                stats['total'] = len(selected_users)
                
                for index, user_data in selected_users:
                    name = user_data.get(name_column, '').strip()
                    email = user_data.get(email_column, '').strip()
                    
                    if name and email:
                        if self.add_user_to_course_by_email(course_id, email, role):
                            stats['successful'] += 1
                            print(f"Enrolled user {index+1}: {name} ({email})")
                        else:
                            stats['failed'] += 1
                    else:
                        print(f"Invalid data at row {index+1}: {user_data}")
                        stats['failed'] += 1
                        
        except Exception as e:
            print(f"Error processing CSV file: {e}")
        
        print(f"Enrollment complete: {stats['successful']}/{stats['total']} users enrolled")
        return stats
    
    def cleanup_courses_by_pattern(self, pattern: str = None, account_id: int = 1) -> int:
        """
        Clean up courses by name pattern
        
        Args:
            pattern: Pattern to match in course names (None for all courses)
            account_id: Account ID to search for courses (default: 1)
            
        Returns:
            Number of courses deleted
        """
        # Get all courses including pagination
        all_courses = []
        
        # Try user courses first
        user_courses = self.canvas.list_courses()
        all_courses.extend(user_courses)
        
        # If no user courses, get account courses with all pages
        if len(user_courses) == 0 and account_id is not None:
            page = 1
            while True:
                result = self.canvas._make_request('GET', f'accounts/{account_id}/courses', 
                                                  params={'per_page': 100, 'page': page})
                if not result or len(result) == 0:
                    break
                all_courses.extend(result)
                
                # Continue to next page regardless of result length
                # Canvas may return fewer than requested even if more pages exist
                page += 1
                
                # Safety check to avoid infinite loop
                if page > 10:  # Reasonable upper limit
                    break
        
        deleted_count = 0
        
        for course in all_courses:
            course_name = course.get('name', '')
            if pattern is None or pattern in course_name:
                if self.canvas.delete_course(course['id']):
                    print(f"Deleted course: {course_name} (ID: {course['id']})")
                    deleted_count += 1
                else:
                    print(f"Failed to delete course: {course_name} (ID: {course['id']})")
        
        return deleted_count
    
    def cleanup_conversations(self, scopes: List[str] = None) -> int:
        """
        Clean up conversations/messages
        
        Args:
            scopes: List of scopes to clean ('inbox', 'sent', 'archived')
            
        Returns:
            Number of conversations deleted
        """
        if scopes is None:
            scopes = ['inbox', 'sent', 'archived']
        
        deleted_count = 0
        for scope in scopes:
            conversations = self.canvas.get_conversations(scope)
            for conversation in conversations:
                if self.canvas.delete_conversation(conversation['id']):
                    subject = conversation.get('subject', 'No subject')
                    print(f"Deleted conversation: {subject} (ID: {conversation['id']})")
                    deleted_count += 1
        
        return deleted_count
    
    def create_course_with_config(self, course_name: str, course_code: str,
                                 account_id: int = 1, **kwargs) -> Optional[Dict]:
        """
        Create a course with additional configuration options
        
        Args:
            course_name: Course name
            course_code: Course code
            account_id: Account ID
            **kwargs: Additional course configuration options
            
        Returns:
            Course data or None if failed
        """
        print(f"Creating course '{course_name}'")
        
        course = self.canvas.create_course(
            name=course_name,
            course_code=course_code,
            account_id=account_id,
            **kwargs
        )
        
        if course:
            course_id = course['id']
            print(f"Course created successfully: {course_name} (ID: {course_id})")
            print(f"Course URL: {self.canvas.base_url}/courses/{course_id}")
            return course
        else:
            print("Failed to create course")
            return None


def create_canvas_utils(task_dir: str = None, canvas_url: str = None, 
                       canvas_token: str = None) -> CanvasPreprocessUtils:
    """
    Factory function to create CanvasPreprocessUtils with automatic config loading
    
    Args:
        task_dir: Task directory path for config loading
        canvas_url: Canvas URL (if None, loaded from config)
        canvas_token: Canvas token (if None, loaded from config)
        
    Returns:
        CanvasPreprocessUtils instance
    """
    # Load Canvas configuration if not provided
    if canvas_url is None or canvas_token is None:
        task_dir_path = Path(task_dir) if task_dir else Path.cwd()
        loaded_url, loaded_token = CanvasTokenManager.get_local_canvas_config(task_dir_path)
        canvas_url = canvas_url or loaded_url
        canvas_token = canvas_token or loaded_token
    
    # Create Canvas API instance
    canvas_api = CanvasAPI(canvas_url, canvas_token)
    
    # Return utils instance
    return CanvasPreprocessUtils(canvas_api)


# Backward compatibility - keep existing classes but mark as deprecated
class CanvasPreprocessPipeline:
    """
    Deprecated: Use CanvasPreprocessUtils instead.
    This class is kept for backward compatibility only.
    """
    
    def __init__(self, task_dir: str = None, canvas_url: str = None, 
                 canvas_token: str = None, agent_workspace: str = None):
        print("DeprecationWarning: CanvasPreprocessPipeline is deprecated. Use CanvasPreprocessUtils instead.")
        self.utils = create_canvas_utils(task_dir, canvas_url, canvas_token)
        self.canvas = self.utils.canvas
        self.course_id = None
    
    def create_course(self, course_name: str, course_code: str, account_id: int = 1) -> bool:
        course = self.utils.create_course_with_config(course_name, course_code, account_id)
        if course:
            self.course_id = course['id']
            return True
        return False
    
    def add_user_to_course(self, user_email: str, role: str = 'StudentEnrollment') -> bool:
        if not self.course_id:
            print("No course available. Create a course first.")
            return False
        return self.utils.add_user_to_course_by_email(self.course_id, user_email, role)


# For compatibility with existing notification task
CanvasNotificationPreprocessPipeline = CanvasPreprocessPipeline
CanvasPreprocessPipelineBase = CanvasPreprocessPipeline