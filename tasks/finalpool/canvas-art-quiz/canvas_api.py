#!/usr/bin/env python3
"""
Canvas REST API Management Library

This module provides a comprehensive interface for managing Canvas courses,
users, enrollments, and other resources using the Canvas REST API.
"""

import requests
import csv
import os
import glob
from typing import Optional, Dict, List, Tuple
import time
from datetime import datetime, timedelta


class CanvasAPI:
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
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, 
                     expect_json: bool = True) -> Optional[Dict]:
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
            print(f"❌ API Error ({method} {endpoint}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Response text: {e.response.text}")
                    print(f"   Response status: {e.response.status_code}")
            return None
    
    def check_course_exists(self, course_name: str, course_code: str, account_id: int = 1) -> Optional[Dict]:
        """
        Check if a course already exists by name or course code
        
        Args:
            course_name: Course name to search for
            course_code: Course code to search for
            account_id: Account ID to search in (default: 1)
            
        Returns:
            Course data if found, None if not found
        """
        try:
            # Search for course by name
            params = {"search_term": course_name}
            result = self._make_request('GET', f'accounts/{account_id}/courses', params=params)
            
            if result:
                # Check for exact name or course code match
                for course in result:
                    if (course.get("name") == course_name or 
                        course.get("course_code") == course_code):
                        course_id = course.get("id")
                        workflow_state = course.get("workflow_state", "unknown")
                        print(f"📍 Course already exists: {course_name} (ID: {course_id}, State: {workflow_state})")
                        return course
                
                print(f"🔍 Course not found: {course_name}")
                return None
            else:
                print(f"❌ Failed to search for course: {course_name}")
                return None
                
        except Exception as e:
            print(f"❌ Error checking if course exists {course_name}: {e}")
            return None
    
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
        # First check if course already exists
        existing_course = self.check_course_exists(name, course_code, account_id)
        if existing_course:
            print(f"✅ Using existing course: {name} (ID: {existing_course['id']})")
            return existing_course
        
        # Create new course if it doesn't exist
        course_data = {
            'course': {
                'name': name,
                'course_code': course_code,
                'is_public': kwargs.get('is_public', True),
                'is_public_to_auth_users': kwargs.get('is_public_to_auth_users', True),
                'public_syllabus': kwargs.get('public_syllabus', True),
                'public_syllabus_to_auth': kwargs.get('public_syllabus_to_auth', True),
                **kwargs
            }
        }
        
        result = self._make_request('POST', f'accounts/{account_id}/courses', course_data)
        if result:
            print(f"✅ Course '{name}' created successfully (ID: {result['id']})")
        return result
    
    def get_course(self, course_id: int) -> Optional[Dict]:
        """Get course information"""
        return self._make_request('GET', f'courses/{course_id}')
    
    def delete_course(self, course_id: int, event: str = 'delete') -> bool:
        """
        Delete or conclude a course using Canvas API
        
        Args:
            course_id: Course ID to delete
            event: Delete event type ('delete' for permanent deletion, 'conclude' for conclusion)
            
        Returns:
            True if successful, False otherwise
        """
        # First get course info for confirmation
        course = self.get_course(course_id)
        if not course:
            print(f"❌ Course {course_id} not found")
            return False
        
        course_name = course.get('name', 'Unknown')
        current_state = course.get('workflow_state', 'unknown')
        
        print(f"🗑️  Attempting to {event} course: {course_name} (ID: {course_id})")
        print(f"   Current state: {current_state}")
        
        # Check if course is already in target state
        if (event == 'delete' and current_state == 'deleted') or \
           (event == 'conclude' and current_state == 'concluded'):
            print(f"✅ Course is already {event}d")
            return True
        
        # Use the correct Canvas API: DELETE with event parameter
        params = {'event': event}
        
        print(f"   Making API request: DELETE courses/{course_id} with params: {params}")
        result = self._make_request('DELETE', f'courses/{course_id}', params=params, expect_json=True)
        
        if result:
            print(f"   API Response: {result}")
            
            # Check for success response (handle both boolean and string values)
            delete_success = result.get('delete') in [True, 'true']
            conclude_success = result.get('conclude') in [True, 'true']
            general_success = result.get('success')
            
            if delete_success or conclude_success or general_success:
                action = "deleted" if event == 'delete' else "concluded"
                print(f"✅ Course '{course_name}' (ID: {course_id}) {action} successfully!")
                
                # Verify the operation by checking the updated course state
                print(f"   Verifying operation...")
                updated_course = self.get_course(course_id)
                if updated_course:
                    actual_state = updated_course.get('workflow_state', 'unknown')
                    print(f"   Verified state: {actual_state}")
                else:
                    print(f"   Course is no longer accessible (likely deleted)")
                
                return True
            else:
                print(f"❌ Unexpected API response: {result}")
                return False
        else:
            print(f"❌ Failed to {event} course {course_id} - API request failed")
            return False
    
    def conclude_course(self, course_id: int) -> bool:
        """
        Conclude a course (soft delete - marks as completed)
        
        Args:
            course_id: Course ID to conclude
            
        Returns:
            True if successful, False otherwise
        """
        return self.delete_course(course_id, event='conclude')
    
    def list_courses(self, include_deleted: bool = False) -> List[Dict]:
        """
        List all courses for the current user
        
        Args:
            include_deleted: Whether to include deleted courses
            
        Returns:
            List of course data
        """
        params = {}
        if include_deleted:
            params['include'] = ['deleted']
        
        result = self._make_request('GET', 'courses', params=params)
        return result if result else []
    
    def publish_course(self, course_id: int) -> bool:
        """
        Publish a course
        
        Args:
            course_id: Course ID to publish
            
        Returns:
            True if successful, False otherwise
        """
        data = {'course': {'event': 'offer'}}
        result = self._make_request('PUT', f'courses/{course_id}', data)
        
        if result and result.get('workflow_state') == 'available':
            print(f"✅ Course {course_id} published successfully!")
            return True
        else:
            print(f"❌ Failed to publish course {course_id}")
            return False
    
    def unpublish_course(self, course_id: int) -> bool:
        """
        Unpublish a course
        
        Args:
            course_id: Course ID to unpublish
            
        Returns:
            True if successful, False otherwise
        """
        data = {'course': {'event': 'claim'}}
        result = self._make_request('PUT', f'courses/{course_id}', data)
        
        if result and result.get('workflow_state') == 'unpublished':
            print(f"✅ Course {course_id} unpublished successfully!")
            return True
        else:
            print(f"❌ Failed to unpublish course {course_id}")
            return False
    
    def create_user(self, name: str, email: str, account_id: int = 1, **kwargs) -> Optional[Dict]:
        """
        Create a new user
        
        Args:
            name: User's full name
            email: User's email address
            account_id: Account ID (default: 1)
            **kwargs: Additional user parameters
            
        Returns:
            User data or None if error
        """
        user_data = {
            'user': {
                'name': name,
                'short_name': kwargs.get('short_name', name.split()[0]),
                'sortable_name': kwargs.get('sortable_name', f"{name.split()[-1]}, {name.split()[0]}"),
                **kwargs
            },
            'pseudonym': {
                'unique_id': email,
                'send_confirmation': kwargs.get('send_confirmation', False),
                **kwargs.get('pseudonym_params', {})
            }
        }
        
        result = self._make_request('POST', f'accounts/{account_id}/users', user_data)
        if result:
            print(f"✅ User '{name}' created successfully (ID: {result['id']})")
        return result
    
    def find_user_by_email(self, email: str, account_id: int = 1) -> Optional[Dict]:
        """
        Find user by email address
        
        Args:
            email: Email address to search for
            account_id: Account ID to search in
            
        Returns:
            User data or None if not found
        """
        params = {'search_term': email}
        result = self._make_request('GET', f'accounts/{account_id}/users', params=params)
        
        if result and len(result) > 0:
            return result[0]
        return None
    
    def get_or_create_user(self, name: str, email: str, account_id: int = 1) -> Optional[Dict]:
        """
        Get existing user or create new one
        
        Args:
            name: User's full name
            email: User's email address
            account_id: Account ID
            
        Returns:
            User data or None if error
        """
        # Try to find existing user first
        user = self.find_user_by_email(email, account_id)
        if user:
            print(f"📍 Found existing user: {name} ({email})")
            return user
        
        # Create new user if not found
        print(f"👤 Creating new user: {name} ({email})")
        return self.create_user(name, email, account_id)
    
    def enroll_user(self, course_id: int, user_id: int, role: str = 'StudentEnrollment', 
                   enrollment_state: str = 'active') -> Optional[Dict]:
        """
        Enroll a user in a course
        
        Args:
            course_id: Course ID
            user_id: User ID to enroll
            role: Enrollment role (StudentEnrollment, TeacherEnrollment, etc.)
            enrollment_state: Enrollment state (active, invited, etc.)
            
        Returns:
            Enrollment data or None if error
        """
        enrollment_data = {
            'enrollment': {
                'user_id': user_id,
                'type': role,
                'enrollment_state': enrollment_state
            }
        }
        
        result = self._make_request('POST', f'courses/{course_id}/enrollments', enrollment_data)
        if result:
            print(f"✅ User {user_id} enrolled as {role} in course {course_id}")
        return result
    
    def load_students_from_csv(self, csv_file_path: str, limit: Optional[int] = None) -> List[Tuple[str, str]]:
        """
        Load student data from CSV file
        
        Args:
            csv_file_path: Path to CSV file with columns: Name, email
            limit: Maximum number of students to load (None for all)
            
        Returns:
            List of (name, email) tuples
        """
        students = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break
                    
                    name = row.get('Name', '').strip()
                    email = row.get('email', '').strip()
                    
                    if name and email:
                        students.append((name, email))
                    else:
                        print(f"⚠️  Skipping invalid row {i+1}: {row}")
            
            print(f"📚 Loaded {len(students)} students from {csv_file_path}")
            return students
            
        except FileNotFoundError:
            print(f"❌ CSV file not found: {csv_file_path}")
            return []
        except Exception as e:
            print(f"❌ Error loading CSV file: {e}")
            return []
    
    def batch_enroll_students(self, course_id: int, students: List[Tuple[str, str]], 
                            account_id: int = 1) -> Dict[str, int]:
        """
        Batch enroll students in a course
        
        Args:
            course_id: Course ID
            students: List of (name, email) tuples
            account_id: Account ID for user creation
            
        Returns:
            Dictionary with enrollment statistics
        """
        stats = {
            'total': len(students),
            'successful': 0,
            'failed': 0,
            'existing_users': 0,
            'new_users': 0
        }
        
        print(f"\n📝 Enrolling {len(students)} students in course {course_id}...")
        
        for i, (name, email) in enumerate(students, 1):
            print(f"\n[{i}/{len(students)}] Processing: {name} ({email})")
            
            # Get or create user
            user = self.get_or_create_user(name, email, account_id)
            if not user:
                print(f"❌ Failed to get/create user: {name}")
                stats['failed'] += 1
                continue
            
            if 'id' in user:
                stats['new_users'] += 1
            else:
                stats['existing_users'] += 1
            
            # Enroll user in course
            enrollment = self.enroll_user(course_id, user['id'], 'StudentEnrollment')
            if enrollment:
                stats['successful'] += 1
            else:
                stats['failed'] += 1
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
        
        print(f"\n📊 Enrollment Summary:")
        print(f"   Total students: {stats['total']}")
        print(f"   Successful enrollments: {stats['successful']}")
        print(f"   Failed enrollments: {stats['failed']}")
        print(f"   New users created: {stats['new_users']}")
        print(f"   Existing users: {stats['existing_users']}")
        
        return stats
    
    def add_teacher_to_course(self, course_id: int, teacher_user_id: int) -> Optional[Dict]:
        """
        Add a teacher to a course
        
        Args:
            course_id: Course ID
            teacher_user_id: Teacher's user ID
            
        Returns:
            Enrollment data or None if error
        """
        return self.enroll_user(course_id, teacher_user_id, 'TeacherEnrollment')
    
    def get_current_user(self) -> Optional[Dict]:
        """
        Get current user information (based on access token)
        
        Returns:
            User data or None if error
        """
        return self._make_request('GET', 'users/self')
    
    # ============================================
    # Assignment Management Functions
    # ============================================
    
    def create_assignment(self, course_id: int, name: str, description: str = "", 
                         points_possible: float = 100, due_at: Optional[str] = None,
                         submission_types: List[str] = None, published: bool = True,
                         **kwargs) -> Optional[Dict]:
        """
        Create an assignment in a course
        
        Args:
            course_id: Course ID
            name: Assignment name
            description: Assignment description/instructions
            points_possible: Maximum points (default: 100)
            due_at: Due date in ISO format (e.g., '2025-12-31T23:59:59Z')
            submission_types: List of allowed submission types
            published: Whether to publish the assignment immediately
            **kwargs: Additional assignment parameters
            
        Returns:
            Assignment data or None if error
        """
        if submission_types is None:
            submission_types = ['online_text_entry', 'online_upload']
        
        assignment_data = {
            'assignment': {
                'name': name,
                'description': description,
                'points_possible': points_possible,
                'submission_types': submission_types,
                'published': published,
                **kwargs
            }
        }
        
        if due_at:
            assignment_data['assignment']['due_at'] = due_at
        
        result = self._make_request('POST', f'courses/{course_id}/assignments', assignment_data)
        if result:
            status = "published" if published else "unpublished"
            print(f"✅ Assignment '{name}' created successfully (ID: {result['id']}, {status})")
        return result
    
    def get_assignment(self, course_id: int, assignment_id: int) -> Optional[Dict]:
        """
        Get assignment details
        
        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            
        Returns:
            Assignment data or None if error
        """
        return self._make_request('GET', f'courses/{course_id}/assignments/{assignment_id}')
    
    def update_assignment(self, course_id: int, assignment_id: int, **kwargs) -> Optional[Dict]:
        """
        Update an assignment
        
        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            **kwargs: Assignment parameters to update
            
        Returns:
            Updated assignment data or None if error
        """
        assignment_data = {'assignment': kwargs}
        result = self._make_request('PUT', f'courses/{course_id}/assignments/{assignment_id}', assignment_data)
        if result:
            print(f"✅ Assignment {assignment_id} updated successfully")
        return result
    
    def publish_assignment(self, course_id: int, assignment_id: int) -> bool:
        """
        Publish an assignment
        
        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            
        Returns:
            True if successful, False otherwise
        """
        result = self.update_assignment(course_id, assignment_id, published=True)
        if result and result.get('published'):
            print(f"✅ Assignment {assignment_id} published successfully!")
            return True
        else:
            print(f"❌ Failed to publish assignment {assignment_id}")
            return False
    
    def list_assignments(self, course_id: int) -> List[Dict]:
        """
        List all assignments in a course
        
        Args:
            course_id: Course ID
            
        Returns:
            List of assignment data
        """
        result = self._make_request('GET', f'courses/{course_id}/assignments')
        return result if result else []
    
    def delete_assignment(self, course_id: int, assignment_id: int, assignment_name: str = "Unknown") -> bool:
        """
        Delete an assignment from a course
        
        Args:
            course_id: Course ID
            assignment_id: Assignment ID to delete
            assignment_name: Assignment name for logging (default: "Unknown")
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🗑️  Deleting assignment: {assignment_name} (ID: {assignment_id}) from course {course_id}")
        
        result = self._make_request('DELETE', f'courses/{course_id}/assignments/{assignment_id}')
        if result:
            print(f"✅ Successfully deleted assignment: {assignment_name} (ID: {assignment_id})")
            return True
        else:
            print(f"❌ Failed to delete assignment: {assignment_name} (ID: {assignment_id})")
            return False
    
    def delete_all_assignments(self, course_id: int) -> bool:
        """
        Delete all assignments in a course
        
        Args:
            course_id: Course ID
            
        Returns:
            True if all assignments deleted successfully, False otherwise
        """
        print(f"\n🗑️  Deleting all assignments in course {course_id}...")
        
        # Get all assignments in the course
        assignments = self.list_assignments(course_id)
        
        if not assignments:
            print(f"✅ No assignments found in course {course_id}")
            return True
        
        print(f"📝 Found {len(assignments)} assignments to delete in course {course_id}")
        
        # Delete each assignment
        success_count = 0
        for assignment in assignments:
            assignment_id = assignment.get("id")
            assignment_name = assignment.get("name", "Unknown")
            
            if self.delete_assignment(course_id, assignment_id, assignment_name):
                success_count += 1
            else:
                print(f"❌ Failed to delete assignment: {assignment_name} (ID: {assignment_id})")
        
        print(f"📊 Deletion Summary: {success_count}/{len(assignments)} assignments deleted successfully")
        
        if success_count == len(assignments):
            print(f"✅ All assignments deleted successfully from course {course_id}")
            return True
        else:
            print(f"⚠️  Some assignments failed to delete from course {course_id}")
            return False
    
    def load_markdown_files(self, directory_path: str, pattern: str = "*.md") -> List[str]:
        """
        Load markdown files from a directory
        
        Args:
            directory_path: Directory path to search
            pattern: File pattern (default: "*.md")
            
        Returns:
            List of markdown file paths
        """
        search_path = os.path.join(directory_path, pattern)
        md_files = glob.glob(search_path)
        
        print(f"📄 Found {len(md_files)} markdown files in {directory_path}")
        for file in md_files:
            print(f"   - {os.path.basename(file)}")
        
        return md_files
    
    def create_assignment_from_md(self, course_id: int, md_file_path: str, 
                                 points_possible: float = 100, due_days_from_now: int = 7,
                                 published: bool = True, **kwargs) -> Optional[Dict]:
        """
        Create an assignment from a markdown file
        
        Args:
            course_id: Course ID
            md_file_path: Path to markdown file
            points_possible: Assignment points
            due_days_from_now: Days from now for due date
            published: Whether to publish immediately
            **kwargs: Additional assignment parameters
            
        Returns:
            Assignment data or None if error
        """
        try:
            # Extract assignment name from filename
            filename = os.path.basename(md_file_path)
            assignment_name = os.path.splitext(filename)[0]
            
            # Read markdown content
            with open(md_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Calculate due date
            due_date = (datetime.now() + timedelta(days=due_days_from_now)).isoformat() + 'Z'
            
            print(f"📝 Creating assignment '{assignment_name}' from {filename}")
            
            # Create assignment
            assignment = self.create_assignment(
                course_id=course_id,
                name=assignment_name,
                description=content,
                points_possible=points_possible,
                due_at=due_date,
                published=published,
                **kwargs
            )
            
            return assignment
            
        except FileNotFoundError:
            print(f"❌ Markdown file not found: {md_file_path}")
            return None
        except Exception as e:
            print(f"❌ Error creating assignment from markdown: {e}")
            return None
    
    def batch_create_assignments_from_md(self, course_id: int, md_directory: str, 
                                       points_possible: float = 100, due_days_interval: int = 7,
                                       published: bool = True, pattern: str = "*.md") -> Dict[str, int]:
        """
        Batch create assignments from markdown files in a directory
        
        Args:
            course_id: Course ID
            md_directory: Directory containing markdown files
            points_possible: Points for each assignment
            due_days_interval: Days between due dates for each assignment
            published: Whether to publish assignments immediately
            pattern: File pattern to match (default: "*.md")
            
        Returns:
            Dictionary with creation statistics
        """
        md_files = self.load_markdown_files(md_directory, pattern)
        
        stats = {
            'total': len(md_files),
            'successful': 0,
            'failed': 0,
            'assignments': []
        }
        
        print(f"\n📚 Creating {len(md_files)} assignments from markdown files...")
        
        for i, md_file in enumerate(md_files):
            print(f"\n[{i+1}/{len(md_files)}] Processing: {os.path.basename(md_file)}")
            
            # Calculate due date (staggered)
            due_days = due_days_interval * (i + 1)
            
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
                    'file': os.path.basename(md_file),
                    'assignment_id': assignment['id'],
                    'name': assignment['name']
                })
            else:
                stats['failed'] += 1
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.2)
        
        print(f"\n📊 Assignment Creation Summary:")
        print(f"   Total files: {stats['total']}")
        print(f"   Successful creations: {stats['successful']}")
        print(f"   Failed creations: {stats['failed']}")
        
        return stats
    
    # ============================================
    # Private Messaging Functions  
    # ============================================
    
    def create_conversation(self, recipients: List[str], subject: str, body: str,
                          context_code: Optional[str] = None) -> Optional[Dict]:
        """
        Create a new conversation (private message)
        
        Args:
            recipients: List of user IDs or email addresses
            subject: Message subject
            body: Message content
            context_code: Context for the conversation (e.g., 'course_123')
            
        Returns:
            Conversation data or None if error
        """
        conversation_data = {
            'recipients': recipients,
            'subject': subject,
            'body': body
        }
        
        if context_code:
            conversation_data['context_code'] = context_code
        
        result = self._make_request('POST', 'conversations', conversation_data)
        if result:
            conv_id = result[0]['id'] if isinstance(result, list) and result else result.get('id', 'Unknown')
            print(f"✅ Conversation created successfully (ID: {conv_id})")
        return result
    
    def send_message_to_user(self, user_id: int, subject: str, body: str, 
                           course_id: Optional[int] = None) -> Optional[Dict]:
        """
        Send a private message to a specific user
        
        Args:
            user_id: Target user ID
            subject: Message subject
            body: Message content
            course_id: Optional course context
            
        Returns:
            Conversation data or None if error
        """
        recipients = [str(user_id)]
        context_code = f'course_{course_id}' if course_id else None
        
        print(f"💬 Sending message to user {user_id}: '{subject}'")
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
            print(f"❌ User not found with email: {email}")
            return None
        
        print(f"📧 Sending message to {user['name']} ({email})")
        return self.send_message_to_user(user['id'], subject, body, course_id)
    
    def get_conversations(self, scope: str = 'inbox') -> List[Dict]:
        """
        Get user's conversations
        
        Args:
            scope: Conversation scope ('inbox', 'sent', 'archived', etc.)
            
        Returns:
            List of conversation data
        """
        params = {'scope': scope}
        result = self._make_request('GET', 'conversations', params=params)
        return result if result else []
    
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
    
    def get_conversation_with_user(self, user_id: int, account_id: int = 1) -> List[Dict]:
        """
        Get conversation history with a specific user
        
        Args:
            user_id: User ID to get conversation with
            account_id: Account ID (for context)
            
        Returns:
            List of conversations with the user
        """
        all_conversations = self.get_conversations('inbox') + self.get_conversations('sent')
        
        user_conversations = []
        for conv in all_conversations:
            # Check if user is in conversation participants
            participants = conv.get('participants', [])
            for participant in participants:
                if participant.get('id') == user_id:
                    user_conversations.append(conv)
                    break
        
        print(f"💬 Found {len(user_conversations)} conversations with user {user_id}")
        return user_conversations
    
    def reply_to_conversation(self, conversation_id: int, body: str) -> Optional[Dict]:
        """
        Reply to an existing conversation
        
        Args:
            conversation_id: Conversation ID to reply to
            body: Reply message content
            
        Returns:
            Message data or None if error
        """
        message_data = {
            'body': body
        }
        
        result = self._make_request('POST', f'conversations/{conversation_id}/add_message', message_data)
        if result:
            print(f"✅ Reply sent to conversation {conversation_id}")
        return result
    
    def batch_message_students(self, student_emails: List[str], subject: str, body: str,
                             course_id: Optional[int] = None, account_id: int = 1) -> Dict[str, int]:
        """
        Send the same message to multiple students
        
        Args:
            student_emails: List of student email addresses
            subject: Message subject
            body: Message content
            course_id: Optional course context
            account_id: Account ID for user lookup
            
        Returns:
            Dictionary with messaging statistics
        """
        stats = {
            'total': len(student_emails),
            'successful': 0,
            'failed': 0
        }
        
        print(f"\n💬 Sending messages to {len(student_emails)} students...")
        print(f"   Subject: {subject}")
        
        for i, email in enumerate(student_emails, 1):
            print(f"\n[{i}/{len(student_emails)}] Messaging: {email}")
            
            result = self.send_message_to_student_by_email(email, subject, body, course_id, account_id)
            if result:
                stats['successful'] += 1
            else:
                stats['failed'] += 1
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.3)
        
        print(f"\n📊 Messaging Summary:")
        print(f"   Total recipients: {stats['total']}")
        print(f"   Successful messages: {stats['successful']}")
        print(f"   Failed messages: {stats['failed']}")
        
        return stats

    # ============================================
    # Quiz Management Functions
    # ============================================
    
    def list_quizzes(self, course_id: int) -> List[Dict]:
        """
        List all quizzes in a course
        
        Args:
            course_id: Course ID
            
        Returns:
            List of quiz data
        """
        result = self._make_request('GET', f'courses/{course_id}/quizzes')
        if result:
            print(f"📝 Found {len(result)} quizzes in course {course_id}")
        return result if result else []
    
    def get_quiz(self, course_id: int, quiz_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific quiz
        
        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            
        Returns:
            Quiz data or None if error
        """
        result = self._make_request('GET', f'courses/{course_id}/quizzes/{quiz_id}')
        if result:
            print(f"📝 Retrieved quiz: {result.get('title', 'Unknown')} (ID: {quiz_id})")
        return result
    
    def get_quiz_questions(self, course_id: int, quiz_id: int) -> List[Dict]:
        """
        Get all questions for a specific quiz
        
        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            
        Returns:
            List of question data with answers and options
        """
        result = self._make_request('GET', f'courses/{course_id}/quizzes/{quiz_id}/questions')
        if result:
            print(f"❓ Found {len(result)} questions in quiz {quiz_id}")
        return result if result else []
    
    def get_quiz_question(self, course_id: int, quiz_id: int, question_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific quiz question
        
        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            question_id: Question ID
            
        Returns:
            Question data with answers and options or None if error
        """
        result = self._make_request('GET', f'courses/{course_id}/quizzes/{quiz_id}/questions/{question_id}')
        if result:
            print(f"❓ Retrieved question {question_id} from quiz {quiz_id}")
        return result
    
    def get_quiz_info(self, course_id: int, quiz_id: int) -> Optional[Dict]:
        """
        Get comprehensive quiz information including all questions, options, and correct answers
        
        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            
        Returns:
            Complete quiz information with questions and answers or None if error
        """
        print(f"\n📝 Getting comprehensive quiz information for quiz {quiz_id}...")
        
        # Get basic quiz information
        quiz_info = self.get_quiz(course_id, quiz_id)
        if not quiz_info:
            print(f"❌ Failed to get quiz {quiz_id} information")
            return None
        
        # Get all questions for the quiz
        questions = self.get_quiz_questions(course_id, quiz_id)
        if not questions:
            print(f"⚠️  No questions found for quiz {quiz_id}")
            quiz_info['questions'] = []
            return quiz_info
        
        # Process each question to extract detailed information
        processed_questions = []
        for question in questions:
            question_data = {
                'id': question.get('id'),
                'question_name': question.get('question_name', ''),
                'question_text': question.get('question_text', ''),
                'question_type': question.get('question_type', ''),
                'points_possible': question.get('points_possible', 0),
                'position': question.get('position', 0),
                'answers': [],
                'correct_answers': []
            }
            
            # Process answers based on question type
            answers = question.get('answers', [])
            for answer in answers:
                answer_data = {
                    'id': answer.get('id'),
                    'text': answer.get('text', ''),
                    'html': answer.get('html', ''),
                    'weight': answer.get('weight', 0),
                    'is_correct': answer.get('weight', 0) > 0
                }
                question_data['answers'].append(answer_data)
                
                # Track correct answers
                if answer_data['is_correct']:
                    question_data['correct_answers'].append(answer_data)
            
            # Handle special question types
            if question.get('question_type') == 'essay_question':
                question_data['question_type'] = 'essay_question'
                question_data['description'] = 'Essay question - no predefined answers'
            elif question.get('question_type') == 'text_only_question':
                question_data['question_type'] = 'text_only_question'
                question_data['description'] = 'Text only question - no answers'
            elif question.get('question_type') == 'file_upload_question':
                question_data['question_type'] = 'file_upload_question'
                question_data['description'] = 'File upload question - no predefined answers'
            
            processed_questions.append(question_data)
        
        # Add processed questions to quiz info
        quiz_info['questions'] = processed_questions
        quiz_info['total_questions'] = len(processed_questions)
        
        # Add summary information
        question_types = {}
        for question in processed_questions:
            q_type = question['question_type']
            question_types[q_type] = question_types.get(q_type, 0) + 1
        
        quiz_info['question_type_summary'] = question_types
        
        print(f"✅ Quiz information retrieved successfully!")
        print(f"   Quiz Title: {quiz_info.get('title', 'Unknown')}")
        print(f"   Total Questions: {quiz_info['total_questions']}")
        print(f"   Question Types: {question_types}")
        
        return quiz_info
    
    def search_quiz_by_title(self, course_id: int, quiz_title: str) -> Optional[Dict]:
        """
        Search for a quiz by title in a course
        
        Args:
            course_id: Course ID
            quiz_title: Quiz title to search for
            
        Returns:
            Quiz data or None if not found
        """
        quizzes = self.list_quizzes(course_id)
        
        for quiz in quizzes:
            if quiz.get('title', '').lower() == quiz_title.lower():
                print(f"📍 Found quiz: {quiz['title']} (ID: {quiz['id']})")
                return quiz
        
        print(f"❌ Quiz with title '{quiz_title}' not found in course {course_id}")
        return None
    
    def get_quiz_statistics(self, course_id: int, quiz_id: int) -> Optional[Dict]:
        """
        Get quiz statistics (requires teacher access)
        
        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            
        Returns:
            Quiz statistics or None if error
        """
        result = self._make_request('GET', f'courses/{course_id}/quizzes/{quiz_id}/statistics')
        if result:
            print(f"📊 Retrieved statistics for quiz {quiz_id}")
        return result

    def delete_quiz(self, course_id: int, quiz_id: int, quiz_title: str = "Unknown") -> bool:
        """
        Delete a quiz from a course
        
        Args:
            course_id: Course ID
            quiz_id: Quiz ID to delete
            quiz_title: Quiz title for logging (default: "Unknown")
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🗑️  Deleting quiz: {quiz_title} (ID: {quiz_id}) from course {course_id}")
        
        result = self._make_request('DELETE', f'courses/{course_id}/quizzes/{quiz_id}')
        if result:
            print(f"✅ Successfully deleted quiz: {quiz_title} (ID: {quiz_id})")
            return True
        else:
            print(f"❌ Failed to delete quiz: {quiz_title} (ID: {quiz_id})")
            return False
    
    def delete_all_quizzes_in_course(self, course_id: int) -> bool:
        """
        Delete all quizzes in a course
        
        Args:
            course_id: Course ID
            
        Returns:
            True if all quizzes deleted successfully, False otherwise
        """
        print(f"\n🗑️  Deleting all quizzes in course {course_id}...")
        
        # Get all quizzes in the course
        quizzes = self.list_quizzes(course_id)
        
        if not quizzes:
            print(f"✅ No quizzes found in course {course_id}")
            return True
        
        print(f"📝 Found {len(quizzes)} quizzes to delete in course {course_id}")
        
        # Delete each quiz
        success_count = 0
        for quiz in quizzes:
            quiz_id = quiz.get("id")
            quiz_title = quiz.get("title", "Unknown")
            
            if self.delete_quiz(course_id, quiz_id, quiz_title):
                success_count += 1
            else:
                print(f"❌ Failed to delete quiz: {quiz_title} (ID: {quiz_id})")
        
        print(f"📊 Deletion Summary: {success_count}/{len(quizzes)} quizzes deleted successfully")
        
        if success_count == len(quizzes):
            print(f"✅ All quizzes deleted successfully from course {course_id}")
            return True
        else:
            print(f"⚠️  Some quizzes failed to delete from course {course_id}")
            return False


class CourseInitializer:
    """Helper class for initializing complete courses"""
    
    def __init__(self, canvas_api: CanvasAPI):
        self.canvas = canvas_api
    
    def initialize_course(self, course_name: str, course_code: str, 
                         csv_file_path: str, student_limit: Optional[int] = None,
                         account_id: int = 1, add_self_as_teacher: bool = True,
                         teacher_email: Optional[str] = "bruiz@mcp.com", publish: bool = True, 
                         **course_kwargs) -> Optional[Dict]:
        """
        Initialize a complete course with students and teacher
        
        Args:
            course_name: Name of the course
            course_code: Course code
            csv_file_path: Path to student CSV file
            student_limit: Maximum number of students to enroll (None for all)
            account_id: Account ID for course creation
            add_self_as_teacher: Whether to add current user as teacher
            teacher_email: Email of specific teacher to add (overrides add_self_as_teacher if provided)
            publish: Whether to publish the course after setup
            **course_kwargs: Additional course parameters
            
        Returns:
            Course data or None if error
        """
        print(f"\n🚀 Initializing course: {course_name} ({course_code})")
        print("=" * 60)
        
        # Step 1: Create course
        print("\n📚 Step 1: Creating course...")
        course = self.canvas.create_course(course_name, course_code, account_id, **course_kwargs)
        if not course:
            print("❌ Failed to create course")
            return None
        
        course_id = course['id']
        
        # Step 2: Add teacher
        if teacher_email or add_self_as_teacher:
            print("\n👨‍🏫 Step 2: Adding teacher to course...")
            
            if teacher_email:
                # Add specific teacher by email
                teacher_user = self.canvas.find_user_by_email(teacher_email, account_id)
                if teacher_user:
                    teacher_enrollment = self.canvas.add_teacher_to_course(course_id, teacher_user['id'])
                    if teacher_enrollment:
                        print(f"✅ Added {teacher_user['name']} ({teacher_email}) as teacher")
                    else:
                        print("❌ Failed to add teacher")
                else:
                    print(f"❌ Could not find user with email: {teacher_email}")
            elif add_self_as_teacher:
                # Add current user as teacher
                current_user = self.canvas.get_current_user()
                if current_user:
                    teacher_enrollment = self.canvas.add_teacher_to_course(course_id, current_user['id'])
                    if teacher_enrollment:
                        print(f"✅ Added {current_user['name']} as teacher")
                    else:
                        print("❌ Failed to add teacher")
                else:
                    print("❌ Could not get current user information")
        
        # Step 3: Load and enroll students
        print("\n👥 Step 3: Loading and enrolling students...")
        students = self.canvas.load_students_from_csv(csv_file_path, student_limit)
        if students:
            enrollment_stats = self.canvas.batch_enroll_students(course_id, students, account_id)
        else:
            print("❌ No students to enroll")

        
        
        # Step 4: Publish course
        if publish:
            print("\n📤 Step 4: Publishing course...")
            if self.canvas.publish_course(course_id):
                print("✅ Course published successfully!")
            else:
                print("❌ Failed to publish course")
        
        # Final summary
        print(f"\n🎉 Course initialization completed!")
        print(f"   Course ID: {course_id}")
        print(f"   Course Name: {course_name}")
        print(f"   Course Code: {course_code}")
        print(f"   Published: {'Yes' if publish else 'No'}")
        
        return course