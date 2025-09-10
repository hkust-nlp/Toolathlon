#!/usr/bin/env python3
"""
Canvas Evaluation Utilities

This module provides utility functions for Canvas LMS task evaluation,
focusing on common operations that can be reused across different tasks.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .api_client import CanvasAPI, CanvasTokenManager


class CanvasEvaluationUtils:
    """Utility functions for Canvas task evaluation"""
    
    def __init__(self, canvas_api: CanvasAPI):
        """
        Initialize evaluation utils with Canvas API instance
        
        Args:
            canvas_api: Initialized CanvasAPI instance
        """
        self.canvas = canvas_api
    
    def find_course_by_name(self, course_name: str, include_deleted: bool = False) -> Optional[Dict]:
        """
        Find a course by name
        
        Args:
            course_name: Course name to search for
            include_deleted: Whether to include deleted courses
            
        Returns:
            Course data or None if not found (returns the most recent one if multiple found)
        """
        matching_courses = []
        
        # Try user courses first
        courses = self.canvas.list_courses(include_deleted=include_deleted)
        for course in courses:
            if course.get('name') == course_name:
                matching_courses.append(course)
        
        # Try account courses (admin access)
        account_courses = []
        try:
            account_courses = self.canvas.list_courses(include_deleted=include_deleted, account_id=1)
            for course in account_courses:
                if course.get('name') == course_name:
                    matching_courses.append(course)
        except:
            # Account access failed
            pass
        
        # Always try checking recently created course IDs to find the newest ones
        # This is needed because Canvas API may not return the newest courses in list
        try:
            # Get the highest course ID from our current list
            all_courses = courses + account_courses
            if all_courses:
                max_id = max(c.get('id', 0) for c in all_courses)
                # Check a few IDs above the max to find recently created courses
                for course_id in range(max_id + 1, max_id + 20):
                    try:
                        course = self.canvas.get_course(course_id)
                        if course and course.get('name') == course_name:
                            matching_courses.append(course)
                    except:
                        continue
        except:
            pass
        
        if matching_courses:
            # Return the course with highest ID (most recent)
            latest_course = max(matching_courses, key=lambda x: x.get('id', 0))
            return latest_course
        
        return None
    
    def verify_course_enrollment(self, course_id: int, expected_students: List[str]) -> Dict:
        """
        Verify that expected students are enrolled in the course
        
        Args:
            course_id: Course ID to check
            expected_students: List of expected student email addresses
            
        Returns:
            Dictionary with verification results
        """
        enrollments = self.canvas.get_course_enrollments(course_id)
        
        # Get enrolled student emails
        enrolled_students = set()
        student_details = []
        
        for enrollment in enrollments:
            if enrollment.get('type') == 'StudentEnrollment':
                user = enrollment.get('user', {})
                user_email = user.get('email') or user.get('login_id', '')
                if user_email:
                    enrolled_students.add(user_email)
                    student_details.append({
                        'name': user.get('name', 'Unknown'),
                        'email': user_email,
                        'id': user.get('id')
                    })
        
        # Compare with expected students
        expected_set = set(expected_students)
        missing_students = expected_set - enrolled_students
        extra_students = enrolled_students - expected_set
        
        return {
            'enrolled_count': len(enrolled_students),
            'expected_count': len(expected_students),
            'missing_students': list(missing_students),
            'extra_students': list(extra_students),
            'enrolled_students': list(enrolled_students),
            'student_details': student_details,
            'all_expected_enrolled': len(missing_students) == 0
        }
    
    def verify_course_assignments(self, course_id: int, expected_assignments: List[str] = None) -> Dict:
        """
        Verify course assignments
        
        Args:
            course_id: Course ID to check
            expected_assignments: Optional list of expected assignment names
            
        Returns:
            Dictionary with assignment verification results
        """
        assignments = self.canvas.list_assignments(course_id)
        
        assignment_details = []
        assignment_names = []
        
        for assignment in assignments:
            assignment_details.append({
                'name': assignment.get('name'),
                'id': assignment.get('id'),
                'published': assignment.get('published', False),
                'points_possible': assignment.get('points_possible'),
                'due_at': assignment.get('due_at')
            })
            assignment_names.append(assignment.get('name'))
        
        result = {
            'assignment_count': len(assignments),
            'assignments': assignment_details,
            'assignment_names': assignment_names
        }
        
        if expected_assignments:
            expected_set = set(expected_assignments)
            actual_set = set(assignment_names)
            
            result.update({
                'expected_count': len(expected_assignments),
                'missing_assignments': list(expected_set - actual_set),
                'extra_assignments': list(actual_set - expected_set),
                'all_expected_present': expected_set.issubset(actual_set)
            })
        
        return result
    
    def verify_private_messages(self, target_emails: List[str], subject_pattern: str = None) -> Dict:
        """
        Verify private messages have been sent to specific users
        
        Args:
            target_emails: List of email addresses to check for messages
            subject_pattern: Optional pattern to match in message subjects
            
        Returns:
            Dictionary with message verification results
        """
        # Get conversations from sent items
        sent_conversations = self.canvas.get_conversations('sent')
        
        message_results = {
            'total_conversations': len(sent_conversations),
            'target_messages': [],
            'verified_emails': set(),
            'all_targets_contacted': False
        }
        
        for conversation in sent_conversations:
            # Get conversation details
            conv_id = conversation.get('id')
            subject = conversation.get('subject', '')
            participants = conversation.get('participants', [])
            
            # Check if conversation matches criteria
            if subject_pattern and subject_pattern not in subject:
                continue
            
            # Check participants for target emails
            for participant in participants:
                participant_email = participant.get('email') or participant.get('login_id', '')
                if participant_email in target_emails:
                    message_results['target_messages'].append({
                        'conversation_id': conv_id,
                        'subject': subject,
                        'recipient_email': participant_email,
                        'recipient_name': participant.get('name', 'Unknown')
                    })
                    message_results['verified_emails'].add(participant_email)
        
        # Check if all targets were contacted
        target_set = set(target_emails)
        message_results['all_targets_contacted'] = target_set.issubset(message_results['verified_emails'])
        message_results['missing_contacts'] = list(target_set - message_results['verified_emails'])
        
        return message_results
    
    def check_course_status(self, course_id: int) -> Dict:
        """
        Check the status of a course
        
        Args:
            course_id: Course ID to check
            
        Returns:
            Dictionary with course status information
        """
        course = self.canvas.get_course(course_id)
        if not course:
            return {'exists': False}
        
        return {
            'exists': True,
            'id': course.get('id'),
            'name': course.get('name'),
            'code': course.get('course_code'),
            'workflow_state': course.get('workflow_state'),
            'published': course.get('workflow_state') == 'available',
            'total_students': course.get('total_students', 0),
            'start_at': course.get('start_at'),
            'end_at': course.get('end_at')
        }


def create_canvas_evaluator(task_dir: str = None, canvas_url: str = None, 
                           canvas_token: str = None) -> CanvasEvaluationUtils:
    """
    Factory function to create CanvasEvaluationUtils with automatic config loading
    
    Args:
        task_dir: Task directory path for config loading
        canvas_url: Canvas URL (if None, loaded from config)
        canvas_token: Canvas token (if None, loaded from config)
        
    Returns:
        CanvasEvaluationUtils instance
    """
    # Load Canvas configuration if not provided
    if canvas_url is None or canvas_token is None:
        task_dir_path = Path(task_dir) if task_dir else Path.cwd()
        loaded_url, loaded_token = CanvasTokenManager.get_local_canvas_config(task_dir_path)
        canvas_url = canvas_url or loaded_url
        canvas_token = canvas_token or loaded_token
    
    # Create Canvas API instance
    canvas_api = CanvasAPI(canvas_url, canvas_token)
    
    # Return evaluator utils instance
    return CanvasEvaluationUtils(canvas_api)


# Backward compatibility - keep existing classes but mark as deprecated
class CanvasEvaluator:
    """
    Deprecated: Use CanvasEvaluationUtils instead.
    This class is kept for backward compatibility only.
    """
    
    def __init__(self, task_dir: str = None, canvas_url: str = None, 
                 canvas_token: str = None):
        print("DeprecationWarning: CanvasEvaluator is deprecated. Use CanvasEvaluationUtils instead.")
        self.utils = create_canvas_evaluator(task_dir, canvas_url, canvas_token)
        self.canvas = self.utils.canvas


class CanvasNotificationEvaluator(CanvasEvaluator):
    """
    Deprecated: Use CanvasEvaluationUtils instead.
    This class is kept for backward compatibility only.
    """
    pass


def run_canvas_notification_evaluation(agent_workspace: str, task_dir: str = None, 
                                     canvas_url: str = None, canvas_token: str = None,
                                     cleanup_after: bool = False) -> Tuple[bool, str]:
    """
    Deprecated: This function contains task-specific logic.
    Task-specific evaluation should be implemented in the task's evaluation/main.py file.
    
    This function is kept for backward compatibility only.
    """
    print("DeprecationWarning: run_canvas_notification_evaluation is deprecated.")
    print("Task-specific evaluation logic should be implemented in evaluation/main.py")
    
    # Basic fallback implementation (ignore unused parameters)
    try:
        evaluator = create_canvas_evaluator(task_dir, canvas_url, canvas_token)
        
        # Simple check - find the course
        course = evaluator.find_course_by_name("Introduction to AI")
        if course:
            return True, f"Course 'Introduction to AI' found (ID: {course['id']})"
        else:
            return False, "Course 'Introduction to AI' not found"
            
    except Exception as e:
        return False, f"Evaluation error: {str(e)}"


# Additional backward compatibility aliases
CanvasEvaluatorBase = CanvasEvaluator
run_basic_canvas_evaluation = run_canvas_notification_evaluation