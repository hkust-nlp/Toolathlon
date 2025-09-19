#!/usr/bin/env python3
"""
Canvas REST API Client

This module provides a comprehensive interface for managing Canvas courses,
users, enrollments, assignments, and messaging using the Canvas REST API.
Based on the implementation from tasks/prepare/canvas-notification-python/canvas_api.py
"""

import requests
import csv
import os
import glob
from typing import Optional, Dict, List, Tuple
import time
from datetime import datetime, timedelta
from pathlib import Path


class CanvasAPI:
    """Main Canvas API client providing comprehensive Canvas operations"""
    
    def __init__(self, base_url: str, access_token: str):
        """
        Initialize Canvas API client
        
        Args:
            base_url: Canvas instance base URL (e.g., 'http://localhost:10001')
            access_token: Canvas API access token
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None, expect_json: bool = True) -> Optional[Dict]:
        """
        Make a request to Canvas API with error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: URL parameters
            expect_json: Whether to expect JSON response (default: True)
            
        Returns:
            Response data or None if error
        """
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data, params=params)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle different response types
            if expect_json:
                if response.content:
                    return response.json()
                else:
                    # Some successful operations return empty content
                    return {'success': True, 'status_code': response.status_code}
            else:
                return {'success': True, 'status_code': response.status_code, 'content': response.text}
            
        except requests.exceptions.RequestException as e:
            print(f"API Error ({method} {endpoint}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    # Error details available in error_data if needed for debugging
                except:
                    # Response parsing failed, status code available in e.response.status_code if needed
                    pass
            return None
    
    # Course Management Methods
    def create_course(self, name: str, course_code: str, account_id: int = 1, **kwargs) -> Optional[Dict]:
        """
        Create a new course
        
        Args:
            name: Course name
            course_code: Course code
            account_id: Account ID (default: 1)
            **kwargs: Additional course parameters
            
        Returns:
            Course data or None if error
        """
        course_data = {
            'course': {
                'name': name,
                'course_code': course_code,
                'account_id': account_id,
                **kwargs
            }
        }
        
        result = self._make_request('POST', f'accounts/{account_id}/courses', course_data)
        if result:
            print(f"Course created successfully: {name} (ID: {result['id']})")
        return result
    
    def delete_course(self, course_id: int, event: str = 'delete') -> bool:
        """
        Delete or conclude a course
        
        Args:
            course_id: Course ID to delete
            event: Delete event type ('delete' for permanent deletion, 'conclude' for conclusion)
            
        Returns:
            True if successful, False otherwise
        """
        # Check current course state
        course = self.get_course(course_id)
        if not course:
            print(f"Course {course_id} not found")
            return False
        
        current_state = course.get('workflow_state', '')
        
        # Skip if already in desired state
        if (event == 'delete' and current_state == 'deleted') or \
           (event == 'conclude' and current_state == 'completed'):
            print(f"Course {course_id} already {current_state}")
            return True
        
        # Perform the operation
        course_update = {
            'course': {
                'event': event
            }
        }
        
        result = self._make_request('PUT', f'courses/{course_id}', course_update)
        if result:
            # Check for success indicators
            delete_success = result.get('delete') in [True, 'true']
            conclude_success = result.get('conclude') in [True, 'true'] 
            general_success = result.get('success') in [True, 'true']
            
            if delete_success or conclude_success or general_success:
                action = "deleted" if event == 'delete' else "concluded"
                print(f"Course {course_id} {action} successfully")
                return True
            else:
                # Verify by checking course state again
                updated_course = self.get_course(course_id)
                if updated_course:
                    new_state = updated_course.get('workflow_state', '')
                    expected_state = 'deleted' if event == 'delete' else 'completed'
                    if new_state == expected_state:
                        print(f"Course {course_id} state updated to {new_state}")
                        return True
                else:
                    print(f"Course is no longer accessible (likely deleted)")
                    return event == 'delete'  # This is expected for delete operations
        
        print(f"Failed to {event} course {course_id}")
        return False
    
    def get_course(self, course_id: int) -> Optional[Dict]:
        """Get course information by ID"""
        return self._make_request('GET', f'courses/{course_id}')
    
    def list_courses(self, include_deleted: bool = False, account_id: int = None) -> List[Dict]:
        """
        List all courses for the current user
        
        Args:
            include_deleted: Whether to include deleted courses
            account_id: If provided, list courses from specific account (admin only)
            
        Returns:
            List of course data
        """
        params = {'per_page': 100}  # Request more items per page
        if include_deleted:
            params['include'] = ['deleted']
        
        all_courses = []
        
        # Try user courses first
        page = 1
        while True:
            params['page'] = page
            result = self._make_request('GET', 'courses', params=params)
            if not result or len(result) == 0:
                break
            all_courses.extend(result)
            if len(result) < params['per_page']:
                break
            page += 1
        
        # If we're admin and no user courses found, try account courses
        if len(all_courses) == 0 and account_id is not None:
            try:
                page = 1
                while True:
                    params['page'] = page
                    result = self._make_request('GET', f'accounts/{account_id}/courses', params=params)
                    if not result or len(result) == 0:
                        break
                    all_courses.extend(result)
                    if len(result) < params['per_page']:
                        break
                    page += 1
            except:
                # Fall back to user courses if account access fails
                pass
        
        return all_courses
    
    def publish_course(self, course_id: int) -> bool:
        """Publish a course to make it available to students"""
        course_update = {
            'course': {
                'event': 'offer'  # Correct way to publish/offer a course
            }
        }
        
        result = self._make_request('PUT', f'courses/{course_id}', course_update)
        if result and result.get('workflow_state') == 'available':
            print(f"Course {course_id} published successfully")
            return True
        elif result:
            print(f"Course {course_id} update succeeded but may not be fully published (state: {result.get('workflow_state')})")
            return True
        return False
    
    def unpublish_course(self, course_id: int) -> bool:
        """Unpublish a course"""
        course_update = {
            'course': {
                'offer': False
            }
        }
        
        result = self._make_request('PUT', f'courses/{course_id}', course_update)
        if result:
            print(f"Course {course_id} unpublished successfully")
            return True
        return False
    
    # User Management Methods
    def get_current_user(self) -> Optional[Dict]:
        """Get current user information"""
        return self._make_request('GET', 'users/self')
    
    def create_user(self, name: str, email: str, account_id: int = 1) -> Optional[Dict]:
        """
        Create a new user
        
        Args:
            name: User's full name
            email: User's email address
            account_id: Account ID (default: 1)
            
        Returns:
            User data or None if error
        """
        user_data = {
            'user': {
                'name': name,
                'short_name': name.split()[0] if name.split() else name,
                'sortable_name': name
            },
            'pseudonym': {
                'unique_id': email,
                'password': 'temppassword123',
                'sis_user_id': email,
                'send_confirmation': False
            }
        }
        
        result = self._make_request('POST', f'accounts/{account_id}/users', user_data)
        return result
    
    def find_user_by_email(self, email: str, account_id: int = 1) -> Optional[Dict]:
        """
        Find a user by email address
        
        Args:
            email: Email address to search for
            account_id: Account ID to search in
            
        Returns:
            User data or None if not found
        """
        try:
            # Direct search APIs are failing with 500 errors, so list all users and filter
            page = 1
            while True:
                params = {'per_page': 100, 'page': page}
                result = self._make_request('GET', f'accounts/{account_id}/users', params=params)
                if not result or len(result) == 0:
                    break
                    
                # Check each user in this page
                for user in result:
                    user_email = user.get('email', user.get('login_id', ''))
                    if user_email == email:
                        return user
                
                page += 1
                # Safety check to avoid infinite loop
                if page > 20:  # Reasonable upper limit
                    break
                        
        except Exception as e:
            print(f"Error searching for user {email}: {e}")
            
        return None
    
    def get_or_create_user(self, email: str, name: str = None, account_id: int = 1) -> Optional[Dict]:
        """
        Get user by email (all users should already exist, no creation needed)
        
        Args:
            name: User's full name (optional)
            email: User's email address
            account_id: Account ID
            
        Returns:
            User data or None if not found
        """
        # Only try to find existing user - don't create new users
        user = self.find_user_by_email(email, account_id)
        if user:
            return user
        
        print(f"User not found: {email} (users should already exist in Canvas)")
        return None
    
    # Enrollment Methods
    def enroll_user(self, course_id: int, user_id: int, role: str = 'StudentEnrollment') -> Optional[Dict]:
        """
        Enroll a user in a course

        Args:
            course_id: Course ID
            user_id: User ID to enroll
            role: Enrollment role (default: 'StudentEnrollment')

        Returns:
            Enrollment data or None if error
        """
        enrollment_data = {
            'enrollment': {
                'user_id': user_id,
                'type': role,
                'enrollment_state': 'active'
            }
        }

        result = self._make_request('POST', f'courses/{course_id}/enrollments', enrollment_data)

        # If we get a success response (even if empty), treat it as successful
        if result and (result.get('success') or result.get('id')):
            return result

        return result
    
    def get_course_enrollments(self, course_id: int) -> List[Dict]:
        """
        Get all enrollments for a course
        
        Args:
            course_id: Course ID
            
        Returns:
            List of enrollment data
        """
        params = {
            'include': ['user'],
            'per_page': 100
        }
        
        all_enrollments = []
        page = 1
        
        while True:
            params['page'] = page
            enrollments = self._make_request('GET', f'courses/{course_id}/enrollments', params=params)
            
            if not enrollments or len(enrollments) == 0:
                break
                
            all_enrollments.extend(enrollments)
            
            # Check if we've reached the last page
            if len(enrollments) < params['per_page']:
                break
            
            page += 1
        
        return all_enrollments
    
    def batch_enroll_students(self, course_id: int, students: List[Tuple[str, str]], 
                             account_id: int = 1) -> Dict[str, int]:
        """
        Enroll multiple students in a course
        
        Args:
            course_id: Course ID
            students: List of (name, email) tuples
            account_id: Account ID
            
        Returns:
            Statistics dictionary with counts
        """
        stats = {'successful': 0, 'failed': 0, 'total': len(students)}
        
        print(f"Enrolling {len(students)} students in course {course_id}...")
        
        for name, email in students:
            try:
                # Get or create user
                user = self.get_or_create_user(name, email, account_id)
                if not user:
                    print(f"Failed to get/create user: {name} ({email})")
                    stats['failed'] += 1
                    continue
                
                # Enroll user in course
                enrollment = self.enroll_user(course_id, user['id'])
                if enrollment:
                    print(f"Enrolled: {name} ({email})")
                    stats['successful'] += 1
                else:
                    print(f"Failed to enroll: {name} ({email})")
                    stats['failed'] += 1
                    
            except Exception as e:
                print(f"Error enrolling {name} ({email}): {e}")
                stats['failed'] += 1
        
        return stats
    
    def add_teacher_to_course(self, course_id: int, user_id: int) -> Optional[Dict]:
        """Add a user as teacher to a course"""
        return self.enroll_user(course_id, user_id, 'TeacherEnrollment')
    
    def load_students_from_csv(self, csv_file_path: str, limit: Optional[int] = None) -> List[Tuple[str, str]]:
        """
        Load students from CSV file
        
        Args:
            csv_file_path: Path to CSV file with Name,email columns
            limit: Maximum number of students to load
            
        Returns:
            List of (name, email) tuples
        """
        students = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    name = row.get('Name', '').strip()
                    email = row.get('email', '').strip()
                    
                    if name and email:
                        students.append((name, email))
                        
                    if limit and len(students) >= limit:
                        break
        except Exception as e:
            print(f"Error reading CSV file: {e}")
        
        return students
    
    # Assignment Methods
    def create_assignment(self, course_id: int, name: str, description: str = "", 
                         points_possible: int = 100, due_at: str = None, 
                         published: bool = True, submission_types: list = None,
                         allowed_extensions: list = None) -> Optional[Dict]:
        """
        Create an assignment
        
        Args:
            course_id: Course ID
            name: Assignment name
            description: Assignment description
            points_possible: Points possible
            due_at: Due date in ISO format
            published: Whether to publish immediately
            submission_types: List of submission types (e.g., ['online_text_entry', 'online_upload'])
            allowed_extensions: List of allowed file extensions for uploads
            
        Returns:
            Assignment data or None if error
        """
        assignment_data = {
            'assignment': {
                'name': name,
                'description': description,
                'points_possible': points_possible,
                'published': published
            }
        }
        
        if due_at:
            assignment_data['assignment']['due_at'] = due_at
        
        if submission_types:
            assignment_data['assignment']['submission_types'] = submission_types
        
        if allowed_extensions:
            assignment_data['assignment']['allowed_extensions'] = allowed_extensions
        
        result = self._make_request('POST', f'courses/{course_id}/assignments', assignment_data)
        return result
    
    def create_assignment_from_md(self, course_id: int, md_file_path: str, 
                                 points_possible: int = 100, due_days_from_now: int = 7,
                                 published: bool = True) -> Optional[Dict]:
        """
        Create assignment from markdown file
        
        Args:
            course_id: Course ID
            md_file_path: Path to markdown file
            points_possible: Points possible
            due_days_from_now: Days from now for due date
            published: Whether to publish immediately
            
        Returns:
            Assignment data or None if error
        """
        try:
            with open(md_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract title from filename or first heading
            file_name = Path(md_file_path).stem
            title = file_name.replace('_', ' ').replace('-', ' ').title()
            
            # Calculate due date
            due_date = datetime.now() + timedelta(days=due_days_from_now)
            due_at = due_date.isoformat() + 'Z'
            
            return self.create_assignment(
                course_id=course_id,
                name=title,
                description=content,
                points_possible=points_possible,
                due_at=due_at,
                published=published
            )
        except Exception as e:
            print(f"Error creating assignment from markdown: {e}")
            return None
    
    def batch_create_assignments_from_md(self, course_id: int, md_directory: str,
                                        points_possible: int = 100, due_days_interval: int = 7,
                                        published: bool = True) -> Dict[str, any]:
        """
        Create multiple assignments from markdown files in directory
        
        Args:
            course_id: Course ID
            md_directory: Directory containing markdown files
            points_possible: Points possible for each assignment
            due_days_interval: Days between assignment due dates
            published: Whether to publish immediately
            
        Returns:
            Statistics dictionary
        """
        md_files = glob.glob(os.path.join(md_directory, "*.md"))
        stats = {'successful': 0, 'failed': 0, 'total': len(md_files), 'assignments': []}
        
        for i, md_file in enumerate(sorted(md_files)):
            due_days = due_days_interval * (i + 1)  # Staggered due dates
            
            assignment = self.create_assignment_from_md(
                course_id=course_id,
                md_file_path=md_file,
                points_possible=points_possible,
                due_days_from_now=due_days,
                published=published
            )
            
            if assignment:
                stats['successful'] += 1
                stats['assignments'].append({
                    'name': assignment['name'],
                    'assignment_id': assignment['id'],
                    'file_path': md_file
                })
            else:
                stats['failed'] += 1
        
        return stats
    
    def list_assignments(self, course_id: int) -> List[Dict]:
        """List all assignments for a course"""
        result = self._make_request('GET', f'courses/{course_id}/assignments')
        return result if result else []
    
    def publish_assignment(self, course_id: int, assignment_id: int) -> bool:
        """Publish an assignment"""
        assignment_update = {
            'assignment': {
                'published': True
            }
        }
        
        result = self._make_request('PUT', f'courses/{course_id}/assignments/{assignment_id}', assignment_update)
        return bool(result)
    
    # Messaging Methods
    def create_conversation(self, recipients: List[str], subject: str, body: str,
                           context_code: Optional[str] = None) -> Optional[Dict]:
        """
        Create a new conversation (private message)
        
        Args:
            recipients: List of user IDs or email addresses
            subject: Message subject
            body: Message body
            context_code: Context for the conversation (e.g., 'course_123')
            
        Returns:
            Conversation data or None if error
        """
        conversation_data = {
            'recipients[]': recipients,
            'subject': subject,
            'body': body
        }
        
        if context_code:
            conversation_data['context_code'] = context_code
        
        result = self._make_request('POST', 'conversations', conversation_data)
        return result
    
    def send_message_to_user(self, user_id: int, subject: str, body: str, 
                            course_id: Optional[int] = None) -> Optional[Dict]:
        """
        Send a private message to a specific user
        
        Args:
            user_id: User ID to send message to
            subject: Message subject
            body: Message body
            course_id: Optional course context
            
        Returns:
            Conversation data or None if error
        """
        recipients = [str(user_id)]
        context_code = f'course_{course_id}' if course_id else None
        
        print(f"Sending message to user {user_id}: '{subject}'")
        return self.create_conversation(recipients, subject, body, context_code)
    
    def send_message_to_student_by_email(self, email: str, subject: str, body: str,
                                        course_id: Optional[int] = None, account_id: int = 1) -> Optional[Dict]:
        """
        Send a private message to a student by email address
        
        Args:
            email: Student's email address
            subject: Message subject
            body: Message content
            course_id: Optional course context
            account_id: Account ID to search for user
            
        Returns:
            Conversation data or None if error
        """
        # Find user by email
        user = self.find_user_by_email(email, account_id)
        if not user:
            print(f"User not found with email: {email}")
            return None
        
        print(f"Sending message to {user['name']} ({email})")
        return self.send_message_to_user(user['id'], subject, body, course_id)
    
    def get_conversations(self, scope: str = 'inbox') -> List[Dict]:
        """
        Get user's conversations (handles pagination)
        
        Args:
            scope: Conversation scope ('inbox', 'sent', 'archived', etc.)
            
        Returns:
            List of conversation data
        """
        params = {
            'scope': scope,
            'per_page': 100  # Request more items per page
        }
        
        all_conversations = []
        page = 1
        
        while True:
            params['page'] = page
            conversations = self._make_request('GET', 'conversations', params=params)
            
            if not conversations or len(conversations) == 0:
                break
                
            all_conversations.extend(conversations)
            
            # Check if we've reached the last page
            if len(conversations) < params['per_page']:
                break
            
            page += 1
        
        return all_conversations
    
    def get_conversation_messages(self, conversation_id: int) -> List[Dict]:
        """
        Get messages in a specific conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of message data
        """
        result = self._make_request('GET', f'conversations/{conversation_id}')
        if result and 'messages' in result:
            return result['messages']
        return []
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete a conversation
        
        Args:
            conversation_id: Conversation ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        result = self._make_request('DELETE', f'conversations/{conversation_id}')
        return bool(result)
    
    def batch_message_students(self, student_emails: List[str], subject: str, body: str,
                              course_id: Optional[int] = None, account_id: int = 1) -> Dict[str, int]:
        """
        Send the same message to multiple students
        
        Args:
            student_emails: List of student email addresses
            subject: Message subject
            body: Message body
            course_id: Optional course context
            account_id: Account ID
            
        Returns:
            Statistics dictionary with counts
        """
        stats = {'successful': 0, 'failed': 0, 'total': len(student_emails)}
        
        print(f"Sending messages to {len(student_emails)} students...")
        
        for email in student_emails:
            try:
                result = self.send_message_to_student_by_email(email, subject, body, course_id, account_id)
                if result:
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"Error sending message to {email}: {e}")
                stats['failed'] += 1
        
        return stats


class CanvasTokenManager:
    """Utility class for managing Canvas tokens and configuration"""
    
    @staticmethod
    def get_local_canvas_config(task_dir: Path = None) -> Tuple[str, str]:
        """
        Load Canvas configuration from local files
        
        Args:
            task_dir: Task directory to search for configuration
            
        Returns:
            Tuple of (canvas_url, canvas_token)
        """
        if task_dir is None:
            task_dir = Path.cwd()
        
        # Try to find token_key_session.py file
        config_file = task_dir / 'token_key_session.py'
        if not config_file.exists():
            # Try parent directories
            for parent in task_dir.parents:
                config_file = parent / 'token_key_session.py'
                if config_file.exists():
                    break
        
        # Default values
        canvas_url = "http://localhost:10001"
        canvas_token = "mcpcanvasadmintoken1"
        
        if config_file.exists():
            try:
                # Simple parsing of the config file
                with open(config_file, 'r') as f:
                    content = f.read()
                    
                # Extract values using string parsing
                if 'canvas_domain' in content:
                    for line in content.split('\n'):
                        if 'canvas_domain' in line and '=' in line:
                            domain = line.split('=')[1].strip().strip('"').strip("'").strip(',')
                            if domain and not domain.startswith('"'):
                                canvas_url = f"http://{domain}" if not domain.startswith('http') else domain
                                break
                
                if 'canvas_api_token' in content:
                    for line in content.split('\n'):
                        if 'canvas_api_token' in line and '=' in line:
                            token = line.split('=')[1].strip().strip(',').strip('"').strip("'")
                            if token and not token.startswith('"') and not token.startswith("'"):
                                canvas_token = token
                                break
                                
            except Exception as e:
                print(f"Error reading config file: {e}")
        
        return canvas_url, canvas_token


# Convenience classes for specific functionality
class CanvasCourseManager(CanvasAPI):
    """Course-specific Canvas operations"""
    pass


class CanvasAssignmentManager(CanvasAPI):
    """Assignment-specific Canvas operations"""
    pass



class CourseInitializer:
    """Helper class for initializing complete courses"""
    
    def __init__(self, canvas_api: CanvasAPI):
        self.canvas = canvas_api
    
    def initialize_course(self, course_name: str, course_code: str, 
                         csv_file_path: str, student_limit: Optional[int] = None,
                         account_id: int = 1, add_self_as_teacher: bool = True,
                         publish: bool = True, **course_kwargs) -> Optional[Dict]:
        """
        Initialize a complete course with students and teacher
        
        Args:
            course_name: Name of the course
            course_code: Course code
            csv_file_path: Path to student CSV file
            student_limit: Maximum number of students to enroll (None for all)
            account_id: Account ID for course creation
            add_self_as_teacher: Whether to add current user as teacher
            publish: Whether to publish the course after setup
            **course_kwargs: Additional course parameters
            
        Returns:
            Course data or None if error
        """
        print(f"\n Initializing course: {course_name} ({course_code})")
        print("=" * 60)
        
        # Step 1: Create course
        print("\n📚 Step 1: Creating course...")
        course = self.canvas.create_course(course_name, course_code, account_id, **course_kwargs)
        if not course:
            print("Failed to create course")
            return None
        
        course_id = course['id']
        
        # Step 2: Add teacher (current user)
        if add_self_as_teacher:
            print("\nStep 2: Adding teacher to course...")
            current_user = self.canvas.get_current_user()
            if current_user:
                teacher_enrollment = self.canvas.add_teacher_to_course(course_id, current_user['id'])
                if teacher_enrollment:
                    print(f" Added {current_user['name']} as teacher")
                else:
                    print("Failed to add teacher")
            else:
                print("Could not get current user information")
        
        # Step 3: Load and enroll students
        print("\n Step 3: Loading and enrolling students...")
        students = self.canvas.load_students_from_csv(csv_file_path, student_limit)
        if students:
            enrollment_stats = self.canvas.batch_enroll_students(course_id, students, account_id)
        else:
            print("No students to enroll")
        
        # Step 4: Publish course
        if publish:
            print("\n Step 4: Publishing course...")
            if self.canvas.publish_course(course_id):
                print(" Course published successfully!")
            else:
                print("Failed to publish course")
        
        # Final summary
        print(f"\n🎉 Course initialization completed!")
        print(f"   Course ID: {course_id}")
        print(f"   Course Name: {course_name}")
        print(f"   Course Code: {course_code}")
        print(f"   Published: {'Yes' if publish else 'No'}")
        
        return course


# Backward compatibility
CanvasAPIClient = CanvasAPI