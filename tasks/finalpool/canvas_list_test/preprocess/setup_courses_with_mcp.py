#!/usr/bin/env python3
"""
Canvas Course Setup Script using direct HTTP API calls
This script sets up courses, enrolls teachers and students, creates announcements, creates quizzes, creates assignments, and publishes courses using Canvas API directly.

Features:
- Create courses with course code and settings
- Check for existing courses to avoid duplicates
- Enroll teachers with TeacherEnrollment role
- Create course announcements for exam information
- Create course quizzes with customized settings
- Create course assignments with customized settings
- Enroll students with StudentEnrollment role
- Publish courses to make them visible to students
- Support for excluding specific students from courses
- Smart handling of existing vs. new courses
- Submit assignments for students automatically

Usage:
    # Create courses with quizzes and assignments (default mode)
    python setup_courses_with_mcp.py
    
    # Delete all courses
    python setup_courses_with_mcp.py --delete
    
    # Publish all unpublished courses
    python setup_courses_with_mcp.py --publish
    
    # Submit assignments for students in CS101 and CS201 courses
    python setup_courses_with_mcp.py --submit-assignments
    
    # Create courses with announcements, quizzes and assignments
    python setup_courses_with_mcp.py --create-announcements
"""

import json
import asyncio
import logging
import sys
import os
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# os.environ["TESSDATA_PREFIX"] = "/ssddata/xiaochen/workspace/mcpbench_dev/scripts"
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from token_key_session import all_token_key_session
# Import Canvas configuration
# from tasks.xiaochen.canvas_list_test.token_key_session import all_token_key_session
CANVAS_API_TOKEN = all_token_key_session.admin_canvas_token
CANVAS_DOMAIN = all_token_key_session.canvas_domain
CANVAS_USER_NAME = all_token_key_session.canvas_user_name
CANVAS_USER_TOKEN = all_token_key_session.canvas_api_token
os.environ["CANVAS_API_TOKEN"] = CANVAS_API_TOKEN
os.environ["CANVAS_DOMAIN"] = CANVAS_DOMAIN

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CanvasCourseSetup:
    def __init__(self):
        self.courses_data = None
        self.users_data = None
        self.base_url = "http://localhost:10001"
        self.headers = {
            "Authorization": f"Bearer {CANVAS_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
    def load_data(self):
        """Load course and user data from JSON files"""
        try:
            # Get the directory of this script's parent directory
            script_dir = Path(__file__).parent.parent
            # Load course configuration
            with open(script_dir / 'files' / 'course_config.json', 'r') as f:
                self.courses_data = json.load(f)
            
            # Load users data
            with open(script_dir / 'files' / 'canvas_users.json', 'r') as f:
                self.users_data = json.load(f)
                
            logger.info("Data loaded successfully")
            print("📊 Data loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    async def get_current_user_profile(self) -> Dict[str, Any]:
        """Get current user's profile information from Canvas API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/users/self/profile"
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        logger.info(f"Successfully retrieved user profile: {user_data.get('name', 'Unknown')}")
                        print(f"👤 Successfully retrieved user profile: {user_data.get('name', 'Unknown')}")
                        return user_data
                    else:
                        logger.error(f"Failed to get user profile: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def check_course_exists(self, course_name: str, course_code: str) -> Optional[str]:
        """Check if a course already exists by name or course code"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/accounts/1/courses"
                params = {"search_term": course_name}
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    if 200 == response.status:
                        courses = await response.json()
                        
                        # Check for exact name or course code match
                        for course in courses:
                            if (course.get("name") == course_name or 
                                course.get("course_code") == course_code):
                                course_id = str(course.get("id"))
                                workflow_state = course.get("workflow_state", "unknown")
                                logger.info(f"Course already exists: {course_name} (ID: {course_id}, State: {workflow_state})")
                                print(f"🏫 Course already exists: {course_name} (ID: {course_id}, State: {workflow_state})")
                                return course_id
                        
                        logger.info(f"Course not found: {course_name}")
                        print(f"🔍 Course not found: {course_name}")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to search for course {course_name}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error checking if course exists {course_name}: {e}")
            return None
    
    async def create_course(self, course_info: Dict[str, Any]) -> str:
        """Create a new course in Canvas via API"""
        try:
            # First check if course already exists
            existing_course_id = await self.check_course_exists(
                course_info["name"], 
                course_info["course_code"]
            )
            
            if existing_course_id:
                logger.info(f"Using existing course: {course_info['name']} (ID: {existing_course_id})")
                print(f"♻️ Using existing course: {course_info['name']} (ID: {existing_course_id})")
                return existing_course_id
            
            # Create new course if it doesn't exist
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/accounts/1/courses"
                course_data = {
                    "course": {
                        "name": course_info["name"],
                        "course_code": course_info["course_code"],
                        "account_id": 1,
                        "enrollment_term_id": 1,
                        "default_view": "modules",
                        "course_format": "on"
                    }
                }
                
                async with session.post(url, headers=self.headers, json=course_data) as response:
                    if 200 == response.status:
                        course_data = await response.json()
                        course_id = course_data.get("id")
                        logger.info(f"Created new course: {course_info['name']} (ID: {course_id})")
                        print(f"✨ Created new course: {course_info['name']} (ID: {course_id})")
                        return str(course_id)
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create course {course_info['name']}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating course {course_info['name']}: {e}")
            return None
    
    async def create_quiz_question(self, course_id: str, quiz_id: str, question_data: Dict[str, Any]) -> bool:
        """Create a quiz question via API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions"
                
                # Prepare question data
                question_payload = {
                    "question": {
                        "question_name": question_data.get("question_name", "Question"),
                        "question_text": question_data["question_text"],
                        "question_type": question_data["question_type"],
                        "points_possible": question_data["points_possible"]
                    }
                }
                
                # Add answers if provided (for multiple choice questions)
                if "answers" in question_data and question_data["answers"]:
                    question_payload["question"]["answers"] = question_data["answers"]
                
                # Add blank_id for fill_in_multiple_blanks_question
                if question_data["question_type"] == "fill_in_multiple_blanks_question" and "answers" in question_data:
                    for answer in question_data["answers"]:
                        if "blank_id" in answer:
                            answer["blank_id"] = answer["blank_id"]
                
                async with session.post(url, headers=self.headers, json=question_payload) as response:
                    if 200 <= response.status < 300:
                        question_response = await response.json()
                        question_id = question_response.get("id")
                        logger.info(f"Created question: '{question_data['question_text'][:50]}...' (ID: {question_id}) in quiz {quiz_id}")
                        print(f"❓ Created question: '{question_data['question_text'][:50]}...' (ID: {question_id}) in quiz {quiz_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create question: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            return False

    async def create_quiz(self, course_id: str, quiz_info: Dict[str, Any]) -> bool:
        """Create a course quiz via API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes"
                
                # Prepare quiz data with all available parameters
                quiz_data = {
                    "quiz": {
                        "title": quiz_info["title"],
                        "description": quiz_info["description"],
                        "quiz_type": quiz_info["quiz_type"],
                        "time_limit": quiz_info["time_limit"],
                        "shuffle_answers": quiz_info["shuffle_answers"],
                        "show_correct_answers": quiz_info["show_correct_answers"],
                        "allowed_attempts": quiz_info["allowed_attempts"],
                        "scoring_policy": quiz_info["scoring_policy"],
                        "points_possible": quiz_info["points_possible"]
                    }
                }
                
                # Add optional parameters if they exist
                if "due_at" in quiz_info and quiz_info["due_at"]:
                    quiz_data["quiz"]["due_at"] = quiz_info["due_at"]
                
                async with session.post(url, headers=self.headers, json=quiz_data) as response:
                    if 200 == response.status:
                        quiz_response = await response.json()
                        quiz_id = quiz_response.get("id")
                        logger.info(f"Created quiz: {quiz_info['title']} (ID: {quiz_id}) in course {course_id}")
                        print(f"📝 Created quiz: {quiz_info['title']} (ID: {quiz_id}) in course {course_id}")
                        
                        # Create quiz questions if provided
                        if "questions" in quiz_info and quiz_info["questions"]:
                            logger.info(f"Creating {len(quiz_info['questions'])} questions for quiz: {quiz_info['title']}")
                            print(f"📋 Creating {len(quiz_info['questions'])} questions for quiz: {quiz_info['title']}")
                            questions_created = 0
                            for question_data in quiz_info["questions"]:
                                if await self.create_quiz_question(course_id, str(quiz_id), question_data):
                                    questions_created += 1
                                else:
                                    logger.warning(f"Failed to create question: {question_data.get('question_text', 'Unknown')[:50]}...")
                            
                            logger.info(f"Created {questions_created}/{len(quiz_info['questions'])} questions for quiz: {quiz_info['title']}")
                            print(f"✅ Created {questions_created}/{len(quiz_info['questions'])} questions for quiz: {quiz_info['title']}")
                        
                        # Publish the quiz
                        if await self.publish_quiz(course_id, quiz_id, quiz_info["title"]):
                            logger.info(f"Published quiz: {quiz_info['title']} (ID: {quiz_id})")
                            print(f"🔔 Published quiz: {quiz_info['title']} (ID: {quiz_id})")
                        else:
                            logger.warning(f"Failed to publish quiz: {quiz_info['title']} (ID: {quiz_id})")
                        
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create quiz {quiz_info['title']}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error creating quiz {quiz_info['title']}: {e}")
            return False
    
    async def publish_quiz(self, course_id: str, quiz_id: str, quiz_title: str) -> bool:
        """Publish a quiz to make it visible to students"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
                publish_data = {
                    "quiz": {
                        "published": True
                    }
                }
                
                async with session.put(url, headers=self.headers, json=publish_data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Published quiz: {quiz_title} (ID: {quiz_id}) in course {course_id}")
                        print(f"📢 Published quiz: {quiz_title} (ID: {quiz_id}) in course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to publish quiz {quiz_title}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error publishing quiz {quiz_title}: {e}")
            return False
    
    async def get_quiz_id(self, course_id: str, quiz_title: str) -> Optional[str]:
        """Get quiz ID by title"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        quizzes = await response.json()
                        
                        # Find exact title match
                        for quiz in quizzes:
                            if quiz.get("title") == quiz_title:
                                return str(quiz.get("id"))
                        
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get quizzes in course {course_id}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting quiz ID for {quiz_title} in course {course_id}: {e}")
            return None
    
    async def is_quiz_published(self, course_id: str, quiz_id: str) -> bool:
        """Check if a quiz is published"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        quiz_data = await response.json()
                        return quiz_data.get("published", False)
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get quiz {quiz_id} details: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error checking if quiz {quiz_id} is published: {e}")
            return False
    
    async def delete_quiz(self, course_id: str, quiz_id: str, quiz_title: str = "Unknown") -> bool:
        """Delete a quiz from a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
                
                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Deleted quiz: {quiz_title} (ID: {quiz_id}) from course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to delete quiz {quiz_title}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting quiz {quiz_title}: {e}")
            return False

    async def delete_all_quizzes_in_course(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all quizzes in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        quizzes = await response.json()
                        
                        if not quizzes:
                            logger.info(f"No quizzes found in course: {course_name}")
                            return True
                        
                        logger.info(f"Found {len(quizzes)} quizzes to delete in course: {course_name}")
                        
                        # Delete each quiz
                        success_count = 0
                        for quiz in quizzes:
                            quiz_id = str(quiz.get("id"))
                            quiz_title = quiz.get("title", "Unknown")
                            
                            if await self.delete_quiz(course_id, quiz_id, quiz_title):
                                success_count += 1
                        
                        logger.info(f"Deleted {success_count}/{len(quizzes)} quizzes from course: {course_name}")
                        return success_count == len(quizzes)
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get quizzes for course {course_name}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting quizzes from course {course_name}: {e}")
            return False

    async def check_quiz_exists(self, course_id: str, quiz_title: str) -> bool:
        """Check if a quiz with the given title already exists in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        quizzes = await response.json()
                        
                        # Check for exact title match
                        for quiz in quizzes:
                            if quiz.get("title") == quiz_title:
                                logger.info(f"Quiz already exists: {quiz_title} (ID: {quiz.get('id')}) in course {course_id}")
                                return True
                        
                        logger.info(f"Quiz not found: {quiz_title} in course {course_id}")
                        return False
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to check quizzes in course {course_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error checking if quiz exists {quiz_title} in course {course_id}: {e}")
            return False
    
    async def create_announcement(self, course_id: str, announcement: Dict[str, str]) -> bool:
        """Create a course announcement via API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics"
                announcement_data = {
                    "title": announcement["title"],
                    "message": announcement["content"],
                    "is_announcement": True,
                    "published": True
                }
                
                async with session.post(url, headers=self.headers, json=announcement_data) as response:
                    if 200 == response.status:
                        logger.info(f"Created announcement: {announcement['title']}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create announcement: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            return False
    
    async def get_course_announcements(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all announcements in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics"
                params = {"only_announcements": "true"}
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    if 200 == response.status:
                        announcements = await response.json()
                        logger.info(f"Found {len(announcements)} announcements in course {course_id}")
                        return announcements
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get announcements for course {course_id}: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error getting announcements for course {course_id}: {e}")
            return []
    
    async def delete_announcement(self, course_id: str, announcement_id: str, announcement_title: str = "Unknown") -> bool:
        """Delete a specific announcement"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics/{announcement_id}"
                
                # Try to delete the announcement
                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Deleted announcement: {announcement_title} (ID: {announcement_id}) from course {course_id}")
                        print(f"🗑️ Deleted announcement: {announcement_title} (ID: {announcement_id})")
                        return True
                    else:
                        # If delete fails, try to unpublish as fallback
                        unpublish_data = {"published": False}
                        async with session.put(url, headers=self.headers, json=unpublish_data) as fallback_response:
                            if 200 <= fallback_response.status < 300:
                                logger.warning(f"Could not delete announcement {announcement_title}, unpublished instead")
                                print(f"⚠️ Could not delete announcement {announcement_title}, unpublished instead")
                                return True
                            else:
                                error_text = await response.text()
                                logger.error(f"Failed to delete announcement {announcement_title}: {response.status} - {error_text}")
                                return False
        except Exception as e:
            logger.error(f"Error deleting announcement {announcement_title}: {e}")
            return False
    
    async def delete_all_announcements_in_course(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all announcements in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get all announcements
                announcements = await self.get_course_announcements(course_id)
                
                if not announcements:
                    logger.info(f"No announcements found in course: {course_name}")
                    print(f"ℹ️ No announcements found in course: {course_name}")
                    return True
                
                logger.info(f"Found {len(announcements)} announcements to delete in course: {course_name}")
                print(f"🗑️ Found {len(announcements)} announcements to delete in course: {course_name}")
                
                # Delete each announcement
                success_count = 0
                for announcement in announcements:
                    announcement_id = str(announcement.get("id"))
                    announcement_title = announcement.get("title", "Unknown")
                    
                    if await self.delete_announcement(course_id, announcement_id, announcement_title):
                        success_count += 1
                
                logger.info(f"Deleted {success_count}/{len(announcements)} announcements from course: {course_name}")
                print(f"✅ Deleted {success_count}/{len(announcements)} announcements from course: {course_name}")
                return success_count == len(announcements)
        except Exception as e:
            logger.error(f"Error deleting announcements from course {course_name}: {e}")
            return False
    
    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find a user in Canvas by email address"""
        try:
            async with aiohttp.ClientSession() as session:
                # Search for user by email in the account
                url = f"{self.base_url}/api/v1/accounts/1/users"
                params = {"search_term": email}
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    if 200 == response.status:
                        users = await response.json()
                        # Find exact email match
                        for user in users:
                            if user.get("login_id") == email or user.get("email") == email:
                                logger.info(f"Found user: {user.get('name', 'Unknown')} (ID: {user.get('id')}) for email: {email}")
                                print(f"👥 Found user: {user.get('name', 'Unknown')} (ID: {user.get('id')}) for email: {email}")
                                return user
                        
                        logger.warning(f"No user found with email: {email}")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to search for user with email {email}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error searching for user with email {email}: {e}")
            return None
    
    async def enroll_student(self, course_id: str, user_email: str, role: str = "StudentEnrollment") -> bool:
        """Enroll a student in a course via API using email"""
        try:
            # Find user by email in Canvas system
            user = await self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User not found in Canvas: {user_email}")
                return False
            
            user_id = user.get("id")
            if not user_id:
                logger.error(f"User found but no ID: {user_email}")
                return False
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/enrollments"
                enrollment_data = {
                    "enrollment": {
                        "user_id": user_id,
                        "type": role,
                        "enrollment_state": "active"
                    }
                }
                
                async with session.post(url, headers=self.headers, json=enrollment_data) as response:
                    if 200 == response.status:
                        logger.info(f"Enrolled {user_email} (ID: {user_id}) in course {course_id}")
                        print(f"🎓 Enrolled {user_email} (ID: {user_id}) in course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to enroll {user_email}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error enrolling {user_email}: {e}")
            return False
    
    async def enroll_teacher(self, course_id: str, teacher_email: str) -> bool:
        """Enroll a teacher in a course via API using email"""
        try:
            # Find teacher by email in Canvas system
            teacher = await self.find_user_by_email(teacher_email)
            if not teacher:
                logger.warning(f"Teacher not found in Canvas: {teacher_email}")
                return False
            
            teacher_id = teacher.get("id")
            if not teacher_id:
                logger.error(f"Teacher found but no ID: {teacher_email}")
                return False
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/enrollments"
                enrollment_data = {
                    "enrollment": {
                        "user_id": teacher_id,
                        "type": "TeacherEnrollment",
                        "enrollment_state": "active"
                    }
                }
                
                async with session.post(url, headers=self.headers, json=enrollment_data) as response:
                    if 200 == response.status:
                        logger.info(f"Enrolled teacher {teacher_email} (ID: {teacher_id}) in course {course_id}")
                        print(f"👨‍🏫 Enrolled teacher {teacher_email} (ID: {teacher_id}) in course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to enroll teacher {teacher_email}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error enrolling teacher {teacher_email}: {e}")
            return False
    
    async def publish_course(self, course_id: str, course_name: str) -> bool:
        """Publish a course to make it visible to students"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}"
                publish_data = {
                    "course": {
                        "event": "offer"
                    }
                }
                
                async with session.put(url, headers=self.headers, json=publish_data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Published course: {course_name} (ID: {course_id})")
                        print(f"🌐 Published course: {course_name} (ID: {course_id})")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to publish course {course_name}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error publishing course {course_name}: {e}")
            return False
    
    async def get_course_status(self, course_id: str) -> Optional[str]:
        """Get the current workflow state of a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}"
                async with session.get(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        course_data = await response.json()
                        workflow_state = course_data.get("workflow_state", "unknown")
                        logger.info(f"Course {course_id} status: {workflow_state}")
                        return workflow_state
                    else:
                        logger.error(f"Failed to get course status for {course_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting course status for {course_id}: {e}")
            return None
    
    async def publish_all_courses(self) -> bool:
        """Publish all unpublished courses in the system (DEPRECATED - now integrated into course creation)"""
        logger.warning("This method is deprecated. Course publishing is now integrated into course creation.")
        logger.info("All courses are automatically published when created.")
        return True
    
    async def setup_course(self, course_info: Dict[str, Any], create_announcements: bool = False) -> bool:
        """Set up a complete course with quizzes and enrollments"""
        try:
            logger.info(f"Setting up course: {course_info['name']}")
            print(f"🚀 Setting up course: {course_info['name']}")
            
            # 1. Create course or get existing course
            course_id = await self.create_course(course_info)
            if not course_id:
                return False
            
            # Check if this is an existing course that was just found
            existing_course_id = await self.check_course_exists(
                course_info["name"], 
                course_info["course_code"]
            )
            is_existing_course = existing_course_id == course_id
            
            if is_existing_course:
                logger.info(f"Setting up existing course: {course_info['name']} (ID: {course_id})")
                print(f"♻️ Setting up existing course: {course_info['name']} (ID: {course_id})")
                # For existing courses, delete all existing quizzes and assignments first
                logger.info(f"Deleting existing quizzes in course: {course_info['name']}")
                print(f"🗑️ Deleting existing quizzes in course: {course_info['name']}")
                await self.delete_all_quizzes_in_course(course_id, course_info['name'])
                logger.info(f"Deleting existing assignments in course: {course_info['name']}")
                print(f"📋 Deleting existing assignments in course: {course_info['name']}")
                await self.delete_all_assignments_in_course(course_id, course_info['name'])
                logger.info(f"Deleting existing announcements in course: {course_info['name']}")
                print(f"📢 Deleting existing announcements in course: {course_info['name']}")
                await self.delete_all_announcements_in_course(course_id, course_info['name'])
            else:
                logger.info(f"Setting up new course: {course_info['name']} (ID: {course_id})")
                print(f"✨ Setting up new course: {course_info['name']} (ID: {course_id})")
            
            # 2. Enroll teacher (if specified)
            teacher_enrolled = False
            if "teacher" in course_info and course_info["teacher"]:
                teacher_enrolled = await self.enroll_teacher(course_id, course_info["teacher"])
                if not teacher_enrolled:
                    logger.warning(f"Failed to enroll teacher for {course_info['name']}")
                else:
                    logger.info(f"Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")
                    print(f"👨‍🏫 Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")
            
            # 3. Create announcement (only if requested and for new courses)
            if create_announcements:
                announcement_created = await self.create_announcement(course_id, course_info["announcement"])
                if not announcement_created:
                    logger.warning(f"Failed to create announcement for {course_info['name']}")
                else:
                    logger.info(f"Successfully created announcement for {course_info['name']}")
                    print(f"📢 Successfully created announcement for {course_info['name']}")
            else:
                logger.info(f"Skipping announcement creation for course: {course_info['name']}")
                print(f"⏩ Skipping announcement creation for course: {course_info['name']}")
            
            # 4. Create quiz (if specified)
            quiz_created = False
            if "quiz" in course_info and course_info["quiz"]:
                # Always create quiz (we already deleted existing ones)
                quiz_created = await self.create_quiz(course_id, course_info["quiz"])
                if not quiz_created:
                    logger.warning(f"Failed to create quiz for {course_info['name']}")
                else:
                    logger.info(f"Successfully created quiz for {course_info['name']}")
                    print(f"📝 Successfully created quiz for {course_info['name']}")
            else:
                logger.info(f"No quiz configuration found for {course_info['name']}")
                print(f"⚠️ No quiz configuration found for {course_info['name']}")
            
            # 5. Create assignment (if specified)
            assignment_created = False
            if "assignment" in course_info and course_info["assignment"]:
                # Always create assignment (we already deleted existing ones)
                assignment_created = await self.create_assignment(course_id, course_info["assignment"])
                if not assignment_created:
                    logger.warning(f"Failed to create assignment for {course_info['name']}")
                else:
                    logger.info(f"Successfully created assignment for {course_info['name']}")
                    print(f"📋 Successfully created assignment for {course_info['name']}")
            else:
                logger.info(f"No assignment configuration found for {course_info['name']}")
                print(f"⚠️ No assignment configuration found for {course_info['name']}")
            
            # 6. Enroll students
            students_to_enroll = course_info["students"].copy()
            
            # Remove excluded students if any
            if "exclude_students" in course_info:
                for excluded_email in course_info["exclude_students"]:
                    if excluded_email in students_to_enroll:
                        students_to_enroll.remove(excluded_email)
                        logger.info(f"Excluded {excluded_email} from {course_info['name']}")
                        print(f"🚫 Excluded {excluded_email} from {course_info['name']}")
            
            # Enroll each student
            enrollment_success = 0
            for student_email in students_to_enroll:
                if await self.enroll_student(course_id, student_email):
                    enrollment_success += 1
            
            logger.info(f"Successfully enrolled {enrollment_success}/{len(students_to_enroll)} students in {course_info['name']}")
            print(f"🎓 Successfully enrolled {enrollment_success}/{len(students_to_enroll)} students in {course_info['name']}")
            
            # 7. Publish course (always publish to ensure visibility)
            course_published = await self.publish_course(course_id, course_info["name"])
            if not course_published:
                logger.warning(f"Failed to publish course {course_info['name']}")
            else:
                logger.info(f"Successfully published course {course_info['name']}")
                print(f"🌐 Successfully published course {course_info['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up course {course_info['name']}: {e}")
            return False
    
    async def run_setup(self):
        """Run the complete course setup process"""
        try:
            logger.info("Starting Canvas course setup...")
            print("🚀 Starting Canvas course setup...")
            
            # Load data
            if not self.load_data():
                return False
            
            # Get current user profile to verify authentication
            logger.info("Getting current user profile...")
            print("👤 Getting current user profile...")
            user_profile = await self.get_current_user_profile()
            if user_profile:
                logger.info(f"Authenticated as: {user_profile.get('name', 'Unknown user')} ({user_profile.get('email', 'No email')})")
                print(f"✅ Authenticated as: {user_profile.get('name', 'Unknown user')} ({user_profile.get('email', 'No email')})")
            else:
                logger.warning("Could not retrieve user profile, but continuing with course setup...")
            
            # Process each course
            success_count = 0
            total_courses = len(self.courses_data["courses"])
            
            for course_info in self.courses_data["courses"]:
                # Default mode: don't create announcements, just quizzes
                if await self.setup_course(course_info, create_announcements=True):
                    success_count += 1
                else:
                    logger.error(f"Failed to set up course: {course_info['name']}")
            
            # Print summary
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"CANVAS COURSE SETUP COMPLETED - {timestamp}")
            print(f"{'='*60}")
            print(f"Total courses processed: {total_courses}")
            print(f"Successfully set up: {success_count}")
            print(f"Failed: {total_courses - success_count}")
            print(f"{'='*60}")
            
            if success_count == total_courses:
                print("✅ All courses set up successfully!")
            else:
                print("⚠️  Some courses failed to set up. Check logs for details.")
            
            return success_count == total_courses
            
        except Exception as e:
            logger.error(f"Fatal error during setup: {e}")
            return False
    
    async def get_all_courses(self) -> List[Dict[str, Any]]:
        """Get all courses from Canvas"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/accounts/1/courses"
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        courses = await response.json()
                        logger.info(f"Retrieved {len(courses)} courses from Canvas")
                        return courses
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get courses: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error getting courses: {e}")
            return []
    
    async def delete_course(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete a course from Canvas"""
        try:
            async with aiohttp.ClientSession() as session:
                # First, conclude the course (required before deletion)
                conclude_url = f"{self.base_url}/api/v1/courses/{course_id}"
                conclude_data = {"event": "conclude"}
                
                async with session.put(conclude_url, headers=self.headers, json=conclude_data) as response:
                    if 200 == response.status:
                        logger.info(f"Concluded course: {course_name} (ID: {course_id})")
                    else:
                        logger.warning(f"Failed to conclude course {course_name}: {response.status}")
                
                # Wait a moment for the conclude operation to complete
                await asyncio.sleep(1)
                
                # Try to delete the course using the event parameter
                delete_url = f"{self.base_url}/api/v1/courses/{course_id}"
                delete_data = {"event": "delete"}
                
                async with session.put(delete_url, headers=self.headers, json=delete_data) as response:
                    if 200 == response.status:
                        logger.info(f"Deleted course: {course_name} (ID: {course_id})")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to delete course {course_name}: {response.status} - {error_text}")
                        
                        # If delete event fails, try alternative approach - deactivate the course
                        logger.info(f"Trying to deactivate course: {course_name} (ID: {course_id})")
                        deactivate_url = f"{self.base_url}/api/v1/courses/{course_id}"
                        deactivate_data = {"course": {"workflow_state": "deleted"}}
                        
                        async with session.put(deactivate_url, headers=self.headers, json=deactivate_data) as response:
                            if 200 == response.status:
                                logger.info(f"Deactivated course: {course_name} (ID: {course_id})")
                                return True
                            else:
                                deactivate_error = await response.text()
                                logger.error(f"Failed to deactivate course {course_name}: {response.status} - {deactivate_error}")
                                return False
        except Exception as e:
            logger.error(f"Error deleting course {course_name}: {e}")
            return False
    
    async def create_assignment(self, course_id: str, assignment_info: Dict[str, Any]) -> bool:
        """Create a course assignment via API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments"
                
                # Prepare assignment data
                assignment_data = {
                    "assignment": {
                        "name": assignment_info["name"],
                        "description": assignment_info["description"],
                        "points_possible": assignment_info["points_possible"],
                        "submission_types": assignment_info["submission_types"],
                        "published": assignment_info.get("published", True)
                    }
                }
                
                # Add optional parameters
                if "due_at" in assignment_info and assignment_info["due_at"]:
                    assignment_data["assignment"]["due_at"] = assignment_info["due_at"]
                
                if "allowed_extensions" in assignment_info and assignment_info["allowed_extensions"]:
                    assignment_data["assignment"]["allowed_extensions"] = assignment_info["allowed_extensions"]
                
                async with session.post(url, headers=self.headers, json=assignment_data) as response:
                    if 200 <= response.status < 300:
                        assignment_response = await response.json()
                        assignment_id = assignment_response.get("id")
                        logger.info(f"Created assignment: {assignment_info['name']} (ID: {assignment_id}) in course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create assignment {assignment_info['name']}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error creating assignment {assignment_info['name']}: {e}")
            return False

    async def check_assignment_exists(self, course_id: str, assignment_name: str) -> bool:
        """Check if an assignment with the given name already exists in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        assignments = await response.json()
                        
                        # Check for exact name match
                        for assignment in assignments:
                            if assignment.get("name") == assignment_name:
                                logger.info(f"Assignment already exists: {assignment_name} (ID: {assignment.get('id')}) in course {course_id}")
                                return True
                        
                        logger.info(f"Assignment not found: {assignment_name} in course {course_id}")
                        return False
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to check assignments in course {course_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error checking if assignment exists {assignment_name} in course {course_id}: {e}")
            return False

    async def delete_assignment(self, course_id: str, assignment_id: str, assignment_name: str = "Unknown") -> bool:
        """Delete an assignment from a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}"
                
                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Deleted assignment: {assignment_name} (ID: {assignment_id}) from course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to delete assignment {assignment_name}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting assignment {assignment_name}: {e}")
            return False

    async def delete_all_assignments_in_course(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all assignments in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        assignments = await response.json()
                        
                        if not assignments:
                            logger.info(f"No assignments found in course: {course_name}")
                            return True
                        
                        logger.info(f"Found {len(assignments)} assignments to delete in course: {course_name}")
                        
                        # Delete each assignment
                        success_count = 0
                        for assignment in assignments:
                            assignment_id = str(assignment.get("id"))
                            assignment_name = assignment.get("name", "Unknown")
                            
                            if await self.delete_assignment(course_id, assignment_id, assignment_name):
                                success_count += 1
                        
                        logger.info(f"Deleted {success_count}/{len(assignments)} assignments from course: {course_name}")
                        return success_count == len(assignments)
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get assignments for course {course_name}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting assignments from course {course_name}: {e}")
            return False

    async def get_assignment_id(self, course_id: str, assignment_name: str) -> Optional[str]:
        """Get assignment ID by name"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments"
                
                async with session.get(url, headers=self.headers) as response:
                    if 200 == response.status:
                        assignments = await response.json()
                        
                        # Find exact name match
                        for assignment in assignments:
                            if assignment.get("name") == assignment_name:
                                return str(assignment.get("id"))
                        
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get assignments in course {course_id}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting assignment ID for {assignment_name} in course {course_id}: {e}")
            return None

    async def submit_assignment_as_student(self, course_id: str, assignment_id: str, user_token: str, submission_data: Dict[str, Any]) -> bool:
        """Submit an assignment as a student using student's token"""
        try:
            # Create student-specific headers
            student_headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
                
                async with session.post(url, headers=student_headers, json=submission_data) as response:
                    if 200 <= response.status < 300:
                        submission_response = await response.json()
                        submission_id = submission_response.get("id")
                        logger.info(f"Submitted assignment (ID: {assignment_id}) as student - Submission ID: {submission_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to submit assignment {assignment_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error submitting assignment {assignment_id}: {e}")
            return False
    
    async def submit_assignments_for_students(self) -> bool:
        """Submit assignments for all students in CS101 and CS201 courses"""
        try:
            logger.info("Starting assignment submissions for students...")
            print("📝 Starting assignment submissions for students...")
            
            # Student tokens mapping (based on canvas_users.json)
            student_tokens = {
                CANVAS_USER_NAME: CANVAS_USER_TOKEN,
             
            }
            
            # Target courses to submit assignments for
            target_courses = ["CS101-1", "CS201-1"]
            
            success_count = 0
            total_submissions = 0
            
            for course_info in self.courses_data["courses"]:
                course_code = course_info.get("course_code")
                if course_code not in target_courses:
                    continue
                
                logger.info(f"Processing course: {course_info['name']} ({course_code})")
                print(f"🏫 Processing course: {course_info['name']} ({course_code})")
                
                # Get course ID
                course_id = await self.check_course_exists(course_info["name"], course_code)
                if not course_id:
                    logger.error(f"Course not found: {course_info['name']}")
                    continue
                
                # Get assignment ID
                if "assignment" not in course_info:
                    logger.warning(f"No assignment found in course: {course_info['name']}")
                    continue
                
                assignment_name = course_info["assignment"]["name"]
                assignment_id = await self.get_assignment_id(course_id, assignment_name)
                if not assignment_id:
                    logger.error(f"Assignment not found: {assignment_name} in course {course_info['name']}")
                    continue
                
                # Submit for each student in this course
                for student_email in course_info.get("students", []):
                    if student_email not in student_tokens:
                        logger.warning(f"No token found for student: {student_email}")
                        continue
                    
                    total_submissions += 1
                    student_token = student_tokens[student_email]
                    
                    # Prepare submission data with custom submission time
                    # Set submission time to a few days before the assignment due date
                    
                    # Generate a random submission time (1-5 days ago)
                    days_ago = random.randint(1, 5)
                    hours_ago = random.randint(1, 23)
                    minutes_ago = random.randint(1, 59)
                    submitted_time = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
                    submitted_at = submitted_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    submission_data = {
                        "submission": {
                            "submission_type": "online_text_entry",
                            "body": f"<p>Assignment submission for {assignment_name}</p><p>Student: {student_email}</p><p>Course: {course_info['name']}</p><p>Submitted at: {submitted_at}</p><p>This is a sample submission demonstrating the assignment submission functionality.</p><p>Content: I have completed the required tasks as specified in the assignment description.</p>",
                            "submitted_at": submitted_at
                        }
                    }
                    
                    # Submit assignment
                    if await self.submit_assignment_as_student(course_id, assignment_id, student_token, submission_data):
                        success_count += 1
                        logger.info(f"✅ Successfully submitted {assignment_name} for {student_email} at {submitted_at}")
                        print(f"✅ Successfully submitted {assignment_name} for {student_email} at {submitted_at}")
                    else:
                        logger.error(f"❌ Failed to submit {assignment_name} for {student_email}")
                        print(f"❌ Failed to submit {assignment_name} for {student_email}")
            
            # Print summary
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"ASSIGNMENT SUBMISSIONS COMPLETED - {timestamp}")
            print(f"{'='*60}")
            print(f"Total submissions attempted: {total_submissions}")
            print(f"Successfully submitted: {success_count}")
            print(f"Failed: {total_submissions - success_count}")
            print(f"{'='*60}")
            
            if success_count == total_submissions:
                print("✅ All assignments submitted successfully!")
            else:
                print("⚠️  Some assignment submissions failed. Check logs for details.")
            
            return success_count == total_submissions
            
        except Exception as e:
            logger.error(f"Fatal error during assignment submissions: {e}")
            return False
    
    async def delete_all_courses(self) -> bool:
        """Delete all courses from Canvas"""
        try:
            logger.info("Starting deletion of all courses...")
            print("🗑️ Starting deletion of all courses...")
            
            # Get all courses
            courses = await self.get_all_courses()
            if not courses:
                logger.info("No courses found to delete")
                print("ℹ️ No courses found to delete")
                return True
            
            # Filter out system courses (usually have specific IDs or names)
            courses_to_delete = []
            for course in courses:
                course_id = str(course.get("id", ""))
                course_name = course.get("name", "Unknown")
                
                # Skip system courses (you can customize this filter)
                # if course_id in ["1", "2", "3"] or "System" in course_name:
                #     logger.info(f"Skipping system course: {course_name} (ID: {course_id})")
                #     continue
                
                courses_to_delete.append({
                    "id": course_id,
                    "name": course_name
                })
            
            if not courses_to_delete:
                logger.info("No user-created courses found to delete")
                print("ℹ️ No user-created courses found to delete")
                return True
            
            logger.info(f"Found {len(courses_to_delete)} courses to delete")
            print(f"🔍 Found {len(courses_to_delete)} courses to delete")
            
            # Delete each course
            success_count = 0
            for course in courses_to_delete:
                if await self.delete_course(course["id"], course["name"]):
                    success_count += 1
                else:
                    logger.error(f"Failed to delete course: {course['name']}")
            
            # Print summary
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"CANVAS COURSE DELETION COMPLETED - {timestamp}")
            print(f"{'='*60}")
            print(f"Total courses to delete: {len(courses_to_delete)}")
            print(f"Successfully deleted: {success_count}")
            print(f"Failed: {len(courses_to_delete) - success_count}")
            print(f"{'='*60}")
            
            if success_count == len(courses_to_delete):
                print("✅ All courses deleted successfully!")
            else:
                print("⚠️  Some courses failed to delete. Check logs for details.")
            
            return success_count == len(courses_to_delete)
            
        except Exception as e:
            logger.error(f"Fatal error during course deletion: {e}")
            return False

async def run_with_args(delete=False, create_announcements=False, submit_assignments=False, agent_workspace=None):
    """Run the setup with specified arguments"""
    setup = CanvasCourseSetup()
    
    if delete:
        print("🗑️  Running in DELETE mode - will delete all courses")
        success = await setup.delete_all_courses()
        if success:
            print("\n🎉 Course deletion completed successfully!")
        else:
            print("\n❌ Course deletion encountered errors. Check logs for details.")
    elif submit_assignments:
        print("📝 Running in SUBMIT ASSIGNMENTS mode - will submit assignments for students")
        # First load data
        if not setup.load_data():
            print("\n❌ Failed to load data for assignment submissions.")
            return
        success = await setup.submit_assignments_for_students()
        if success:
            print("\n🎉 Assignment submissions completed successfully!")
        else:
            print("\n❌ Assignment submissions encountered errors. Check logs for details.")
    else:
        if create_announcements:
            print("🚀 Running in SETUP mode - will create courses with quizzes, assignments and announcements (auto-published)")
        else:
            print("🚀 Running in SETUP mode - will create courses with quizzes and assignments (no announcements, auto-published)")
        success = await setup.run_setup()
        if success:
            print("\n🎉 Course setup completed successfully!")
        else:
            print("\n❌ Course setup encountered errors. Check logs for details.")

async def main(delete=False, create_announcements=False, submit_assignments=False, agent_workspace=None):
    """Main function that can accept external arguments"""
    # 如果没有传入参数，则从命令行解析
    if delete is False and create_announcements is False and submit_assignments is False and agent_workspace is None:
        import argparse
        
        # 创建参数解析器
        parser = argparse.ArgumentParser(description='Canvas Course Setup Tool')
        parser.add_argument('--delete', action='store_true', help='Delete all courses')
        parser.add_argument('--create_announcements', action='store_true', help='Create announcements along with quizzes')
        parser.add_argument('--submit_assignments', action='store_true', help='Submit assignments for students in CS101 and CS201')
        parser.add_argument('--agent_workspace', help='Agent workspace path')
        
        # 解析参数
        args = parser.parse_args()
        delete = args.delete
        create_announcements = args.create_announcements
        submit_assignments = args.submit_assignments
        agent_workspace = args.agent_workspace
    
    # 调用run_with_args函数
    await run_with_args(delete=delete, create_announcements=create_announcements, submit_assignments=submit_assignments, agent_workspace=agent_workspace)

if __name__ == "__main__":
    asyncio.run(main())
