#!/usr/bin/env python3
"""
Canvas Course Setup Script using direct HTTP API calls
This script sets up courses, enrolls teachers and students, creates announcements, and publishes courses using Canvas API directly.

Features:
- Create courses with course code and settings
- Check for existing courses to avoid duplicates
- Enroll teachers with TeacherEnrollment role
- Create course announcements for exam information
- Enroll students with StudentEnrollment role
- Publish courses to make them visible to students
- Support for excluding specific students from courses
- Smart handling of existing vs. new courses

Usage:
    # Create courses (default mode)
    python setup_courses_with_mcp.py
    
    # Delete all courses
    python setup_courses_with_mcp.py --delete
    
    # Publish all unpublished courses
    python setup_courses_with_mcp.py --publish
"""

import json
import asyncio
import logging
import sys
import os
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import Canvas configuration
from pathlib import Path
import importlib

# Import token_key_session using relative import (when using -m)

local_token_key_session_file = os.path.join(os.path.dirname(__file__),'..', "token_key_session.py")
if os.path.exists(local_token_key_session_file):
    spec = importlib.util.spec_from_file_location("token_key_session", local_token_key_session_file)
    token_key_session_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(token_key_session_module)
    all_token_key_session = token_key_session_module.all_token_key_session
else:
    raise FileNotFoundError(f"Token key session file not found: {local_token_key_session_file}")

# Import app_specific Canvas modules
from utils.app_specific.canvas import CanvasAPI, AnnouncementManager

ADMIN_CANVAS_API_TOKEN = all_token_key_session.admin_canvas_token
# CANVAS_DOMAIN = all_token_key_session.canvas_domain
# os.environ["CANVAS_API_TOKEN"] = ADMIN_CANVAS_API_TOKEN
# os.environ["CANVAS_DOMAIN"] = CANVAS_DOMAIN


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
            "Authorization": f"Bearer {ADMIN_CANVAS_API_TOKEN}",
            "Content-Type": "application/json"
        }

        # Initialize app_specific Canvas API for reusable operations
        self.canvas_api = CanvasAPI(self.base_url, ADMIN_CANVAS_API_TOKEN)
        self.announcement_manager = AnnouncementManager(self.canvas_api)
        
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
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    async def get_current_user_profile(self) -> Dict[str, Any]:
        """Get current user's profile information from Canvas API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/users/self/profile"
                print(url)
                print(self.headers)
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        logger.info(f"Successfully retrieved user profile: {user_data.get('name', 'Unknown')}")
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
                                return course_id
                        
                        logger.info(f"Course not found: {course_name}")
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
                print(f"✅ Using existing course: {course_info['name']} (ID: {existing_course_id})")
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
                        return str(course_id)
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to create course {course_info['name']}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating course {course_info['name']}: {e}")
            return None
    
    async def create_announcement(self, course_id: str, announcement: Dict[str, str]) -> bool:
        """Create a course announcement via API"""
        try:
            # Use app_specific AnnouncementManager
            result = self.announcement_manager.create_announcement(
                course_id=int(course_id),
                title=announcement["title"],
                message=announcement["content"],
                is_announcement=True
            )

            if result:
                logger.info(f"Created announcement: {announcement['title']}")
                return True
            else:
                logger.error(f"Failed to create announcement: {announcement['title']}")
                return False
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            return False
    
    def generate_additional_announcements(self, course_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate additional realistic announcements for a course"""
        course_name = course_info["name"]
        course_code = course_info["course_code"]
        
        # Basic announcement template
        announcements = []
        
        # 1. Course start welcome announcement
        # Build exam type information
        exam_type = course_info.get("exam_type", "TBD")
        if exam_type == "no_exam":
            exam_type_display = "No Final Exam"
        else:
            exam_type_display = exam_type.replace("_", " ").title()
        
        # Build credit information
        credits = course_info.get("credits", "TBD")
        
        announcements.append({
            "title": f"Welcome to {course_code}!",
            "content": f"Dear {course_code} students,\n\nWelcome to {course_name}! I'm excited to have you in this course.\n\n🏫 Course Information:\n🎓 Credits: {credits}\n📝 Exam Type: {exam_type_display}\n\n📚 Course Materials:\n- Please check the syllabus for required textbooks\n- All lecture slides will be posted on Canvas\n- Office hours: Tuesdays and Thursdays 2:00-4:00 PM\n\n💡 Important Notes:\n- Please introduce yourself in the discussion forum\n- Check your email regularly for course updates\n- Don't hesitate to ask questions!\n\nLooking forward to a great semester!\n\nBest regards,\nCourse Instructor"
        })
        
        # 2. First assignment announcement (October)
        if "CS" in course_code or "AI" in course_code or "NET" in course_code or "DB" in course_code:
            announcements.append({
                "title": f"Assignment 1 Released - {course_code}",
                "content": f"Dear {course_code} students,\n\n📝 Assignment 1 has been released and is now available under the Assignments tab.\n\n📅 Due Date: October 15, 2024, 11:59 PM\n📊 Weight: 15% of final grade\n⏱️ Estimated Time: 8-10 hours\n\n📋 Assignment Details:\n- Programming assignment focusing on fundamental concepts\n- Submit your code files (.py, .java, or .cpp)\n- Include a README file with instructions\n- Follow the coding style guidelines\n\n💻 Submission:\n- Upload files to Canvas before the deadline\n- Late submissions: -10% per day\n\nGood luck!\n\nBest regards,\nCourse Instructor"
            })
        elif "MATH" in course_code:
            announcements.append({
                "title": f"Problem Set 1 Released - {course_code}",
                "content": f"Dear {course_code} students,\n\n📝 Problem Set 1 has been posted and is available under Assignments.\n\n📅 Due Date: October 12, 2024, 11:59 PM\n📊 Weight: 12% of final grade\n⏱️ Estimated Time: 6-8 hours\n\n📋 Assignment Details:\n- 8 problems covering chapters 1-3\n- Show all work for full credit\n- Handwritten solutions are acceptable\n- Scan and upload as PDF if handwritten\n\n💡 Tips:\n- Start early - some problems are challenging\n- Attend office hours if you need help\n- Form study groups (but submit individual work)\n\nBest regards,\nCourse Instructor"
            })
        elif "ENG" in course_code:
            announcements.append({
                "title": f"Essay Assignment 1 - {course_code}",
                "content": f"Dear {course_code} students,\n\n📝 Your first essay assignment is now available.\n\n📅 Due Date: October 18, 2024, 11:59 PM\n📊 Weight: 20% of final grade\n📄 Length: 1000-1200 words\n\n📋 Assignment Details:\n- Topic: 'The Impact of Technology on Modern Communication'\n- Use MLA format\n- Minimum 5 academic sources required\n- Submit as PDF or Word document\n\n✍️ Requirements:\n- Clear thesis statement\n- Well-structured arguments\n- Proper citations and bibliography\n- Proofread for grammar and style\n\nBest regards,\nCourse Instructor"
            })
        
        # 3. Midterm exam or quiz announcement (November)
        if course_info.get("exam_type") != "no_exam":
            announcements.append({
                "title": f"Midterm Exam Information - {course_code}",
                "content": f"Dear {course_code} students,\n\n📅 Midterm Exam Schedule:\n\n📅 Date: November 12, 2024\n⏰ Time: Regular class time\n⏱️ Duration: 75 minutes\n📍 Location: Regular classroom\n\n📚 Exam Coverage:\n- Chapters 1-6 from textbook\n- All lecture materials through Week 8\n- Homework assignments 1-4\n\n📝 Format:\n- Multiple choice (40%)\n- Short answer questions (35%)\n- Problem solving (25%)\n\n💡 Study Tips:\n- Review lecture slides and notes\n- Practice problems from homework\n- Attend review session on November 10\n\nGood luck with your preparation!\n\nBest regards,\nCourse Instructor"
            })
        
        # 4. Project announcement (for programming courses) (December)
        if "CS" in course_code or "AI" in course_code or "NET" in course_code or "DB" in course_code:
            announcements.append({
                "title": f"Group Project Announcement - {course_code}",
                "content": f"Dear {course_code} students,\n\n🚀 Group Project has been announced!\n\n👥 Team Size: 3-4 students\n📅 Project Due: December 15, 2024\n📊 Weight: 25% of final grade\n\n🎯 Project Options:\n1. Web application development\n2. Data analysis and visualization\n3. Machine learning implementation\n4. Mobile app development\n\n📋 Deliverables:\n- Source code with documentation\n- Technical report (10-15 pages)\n- 15-minute presentation\n- Demo video (5 minutes)\n\n📅 Important Dates:\n- Team formation: November 20, 2024\n- Project proposal: November 25, 2024\n- Progress report: December 5, 2024\n- Final submission: December 15, 2024\n- Presentations: December 16-18, 2024\n\nStart forming your teams!\n\nBest regards,\nCourse Instructor"
            })
        elif "MATH" in course_code:
            announcements.append({
                "title": f"Research Project - {course_code}",
                "content": f"Dear {course_code} students,\n\n📊 Individual Research Project Announced!\n\n📅 Due Date: December 12, 2024\n📊 Weight: 20% of final grade\n\n🎯 Project Requirements:\n- Choose a mathematical topic related to course material\n- Write a 8-10 page research paper\n- Include mathematical proofs or applications\n- Present findings to the class (10 minutes)\n\n📋 Suggested Topics:\n- Applications of linear algebra in computer graphics\n- Mathematical modeling in real-world problems\n- Historical development of key theorems\n- Computational methods and algorithms\n\n📅 Timeline:\n- Topic selection: November 15, 2024\n- Outline submission: November 25, 2024\n- Draft for peer review: December 5, 2024\n- Final submission: December 12, 2024\n\nBest regards,\nCourse Instructor"
            })
        
        # # 5. Important notice announcement (final preparation period - early December)
        # announcements.append({
        #     "title": f"Final Exam Preparation Updates - {course_code}",
        #     "content": f"Dear {course_code} students,\n\n📢 Important updates as we approach the final exam period:\n\n🚨 Final Exam Reminders:\n- Final exam scheduled for January 2025 (check course announcement for exact date)\n- Review sessions will be scheduled during the last week of classes\n- Office hours extended during exam period (Mon-Fri 1-4 PM)\n\n📚 Study Resources:\n- Comprehensive study guide now available\n- Past exam samples posted for practice\n- All lecture recordings accessible until end of semester\n\n🗓️ End-of-Semester Schedule:\n- Last day of classes: December 20, 2024\n- Final project presentations: December 16-18, 2024\n- Course evaluations due: December 22, 2024\n\n💡 Study Tips:\n- Start reviewing early - don't wait until exam week\n- Form study groups to discuss difficult concepts\n- Attend review sessions for clarification\n\n💬 Questions?\nFeel free to post in the discussion forum or attend office hours.\n\nBest regards,\nCourse Instructor"
        # })
        
        return announcements
    
    async def create_multiple_announcements(self, course_id: str, course_info: Dict[str, Any]) -> bool:
        """Create announcements in chronological order (earliest to latest)"""
        success_count = 0
        total_announcements = 0
        
        try:
            # 1. First create early semester announcements (September-December, in chronological order)
            additional_announcements = self.generate_additional_announcements(course_info)
            print(f"📝 Creating {len(additional_announcements)} semester announcements for {course_info['name']} (Sep-Dec 2024)")
            
            for i, announcement in enumerate(additional_announcements, 1):
                print(f"🔄 Creating announcement {i}/{len(additional_announcements)}: {announcement['title']}")
                announcement_created = await self.create_announcement(course_id, announcement)
                total_announcements += 1
                if announcement_created:
                    success_count += 1
                    print(f"✅ Semester announcement {i} created successfully")
                else:
                    print(f"❌ Failed to create semester announcement {i}")
                
                # Small interval to avoid API calls being too frequent
                await asyncio.sleep(0.3)
            
            # 2. Finally create final exam announcement (January 2025)
            print(f"📢 Creating final exam announcement for {course_info['name']} (Jan 2025)")
            main_announcement_created = await self.create_announcement(course_id, course_info["announcement"])
            total_announcements += 1
            if main_announcement_created:
                success_count += 1
                print(f"✅ Final exam announcement created successfully")
            else:
                print(f"❌ Failed to create final exam announcement")
            
            print(f"📊 Announcement Summary for {course_info['name']}: {success_count}/{total_announcements} created successfully")
            print(f"📅 Timeline: Semester announcements (Sep-Dec 2024) → Final exam (Jan 2025)")
            
            return success_count > 0  # At least one announcement created successfully
            
        except Exception as e:
            logger.error(f"Error creating multiple announcements for {course_info['name']}: {e}")
            print(f"💥 Error creating announcements for {course_info['name']}: {e}")
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
        """Delete a specific announcement using app_specific module"""
        try:
            # Use app_specific AnnouncementManager for deletion
            success = self.announcement_manager.delete_announcement(
                int(course_id),
                int(announcement_id)
            )

            if success:
                logger.info(f"Successfully deleted announcement: {announcement_title}")
                print(f"✅ Successfully deleted announcement: {announcement_title}")
                return True
            else:
                logger.warning(f"Failed to delete announcement: {announcement_title}")
                print(f"⚠️ Could not delete announcement: {announcement_title}")
                return False

        except Exception as e:
            logger.error(f"Error deleting announcement {announcement_title}: {e}")
            print(f"💥 Error deleting announcement '{announcement_title}': {e}")
            return False

    async def delete_all_announcements(self, course_id: str, course_name: str) -> int:
        """Delete all announcements in a course"""
        try:
            # Get all announcements using app_specific module
            announcements = self.announcement_manager.list_announcements(int(course_id))

            if not announcements:
                logger.info(f"No announcements found in course {course_name} (ID: {course_id})")
                print(f"ℹ️ No announcements to delete in course {course_name} (ID: {course_id})")
                return 0

            deleted_count = 0
            print(f"🗑️ Found {len(announcements)} announcements to delete in course {course_name} (ID: {course_id})")

            for announcement in announcements:
                announcement_id = announcement.get("id")
                announcement_title = announcement.get("title", "Unknown")

                success = await self.delete_announcement(course_id, str(announcement_id), announcement_title)
                if success:
                    deleted_count += 1

                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.2)

            logger.info(f"Deleted {deleted_count}/{len(announcements)} announcements from course {course_name} (ID: {course_id})")
            print(f"📊 Deleted {deleted_count}/{len(announcements)} announcements from course {course_name} (ID: {course_id})")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting all announcements from course {course_name} (ID: {course_id}): {e}")
            print(f"💥 Error deleting all announcements from course {course_name} (ID: {course_id}): {e}")
            return 0

    async def enroll_teacher(self, course_id: str, teacher_email: str) -> bool:
        """Enroll a teacher in the course using app_specific module"""
        try:
            # Find or create teacher user using app_specific module
            teacher = self.canvas_api.get_or_create_user(
                email=teacher_email,
                account_id=1
            )
            # Enroll as teacher using app_specific module
            if not teacher:
                logger.error(f"Failed to find teacher: {teacher_email}")
                return False

            # Enroll as teacher using app_specific module
            enrollment = self.canvas_api.add_teacher_to_course(int(course_id), int(teacher["id"]))

            if enrollment:
                logger.info(f"Enrolled teacher {teacher_email} in course {course_id}")
                return True
            else:
                logger.error(f"Failed to enroll teacher {teacher_email}")
                return False

        except Exception as e:
            logger.error(f"Error enrolling teacher: {e}")
            raise
    
    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find a user in Canvas by email address using app_specific module"""
        try:
            # Use app_specific module to find user
            user = self.canvas_api.find_user_by_email(email, account_id=1)
            if user:
                logger.info(f"Found user: {user.get('name', 'Unknown')} (ID: {user.get('id')}) for email: {email}")
                return user
            else:
                logger.warning(f"No user found with email: {email}")
                return None
        except Exception as e:
            logger.error(f"Error finding user by email {email}: {e}")
            return None

    async def enroll_student(self, course_id: str, user_email: str, role: str = "StudentEnrollment") -> bool:
        """Enroll a student in the course using app_specific module"""
        try:
            # Find user by email
            user = await self.find_user_by_email(user_email)
            if not user:
                logger.error(f"Cannot enroll student - user not found: {user_email}")
                return False

            # Enroll user using app_specific module
            enrollment = self.canvas_api.enroll_user(
                course_id=int(course_id),
                user_id=user["id"],
                role=role
            )

            if enrollment:
                logger.info(f"Enrolled student {user_email} in course {course_id}")
                return True
            else:
                logger.error(f"Failed to enroll student {user_email}")
                return False

        except Exception as e:
            logger.error(f"Error enrolling student {user_email}: {e}")
            return False

    async def enroll_students(self, course_id: str, students: List[Dict[str, str]], exclude_emails: List[str] = []) -> int:
        """Enroll multiple students in the course using app_specific module"""
        enrolled_count = 0

        for student in students:
            student_email = student.get("email", "")
            student_name = student.get("name", "")

            # Skip excluded students
            if student_email in exclude_emails:
                logger.info(f"Skipping excluded student: {student_name} ({student_email})")
                continue

            try:
                # Use app_specific module to get or create user
                user = self.canvas_api.get_or_create_user(
                    name=student_name,
                    email=student_email,
                    account_id=1
                )

                if not user:
                    logger.error(f"Failed to find/create student: {student_name} ({student_email})")
                    continue

                # Enroll as student
                enrollment = self.canvas_api.enroll_user(
                    course_id=int(course_id),
                    user_id=user["id"],
                    role='StudentEnrollment'
                )

                if enrollment:
                    enrolled_count += 1
                    logger.info(f"Enrolled student {student_name} ({student_email}) in course {course_id}")
                else:
                    logger.error(f"Failed to enroll student {student_name} ({student_email})")

            except Exception as e:
                logger.error(f"Error enrolling student {student_name} ({student_email}): {e}")

        return enrolled_count
    
    async def get_course_enrollments(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all enrollments in a course using app_specific module"""
        try:
            enrollments = self.canvas_api.get_course_enrollments(int(course_id))
            logger.info(f"Found {len(enrollments)} enrollments in course {course_id}")
            return enrollments
        except Exception as e:
            logger.error(f"Error getting enrollments for course {course_id}: {e}")
            return []

    async def remove_enrollment(self, course_id: str, enrollment_id: str, user_email: str = "Unknown") -> bool:
        """Remove a specific enrollment from a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/enrollments/{enrollment_id}"
                data = {
                    "task": "delete"
                }

                async with session.delete(url, headers=self.headers, json=data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Removed enrollment for {user_email} from course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to remove enrollment {enrollment_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error removing enrollment {enrollment_id}: {e}")
            return False

    async def remove_all_enrollments(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Remove all enrollments from a course (teachers and students)"""
        try:
            # Get all enrollments
            enrollments = await self.get_course_enrollments(course_id)

            if not enrollments:
                logger.info(f"No enrollments found in course {course_name} (ID: {course_id})")
                return True

            # Get current admin user profile to check if admin is enrolled
            admin_profile = await self.get_current_user_profile()
            admin_id = admin_profile.get("id") if admin_profile else None
            admin_email = admin_profile.get("primary_email", admin_profile.get("email", "admin")) if admin_profile else "admin"

            logger.info(f"Removing {len(enrollments)} enrollments from course {course_name} (ID: {course_id})")
            print(f"🗑️ Removing {len(enrollments)} existing enrollments from course {course_name}")

            # Remove each enrollment
            success_count = 0
            admin_removed = False
            for enrollment in enrollments:
                enrollment_id = str(enrollment.get("id", ""))
                enrollment_type = enrollment.get("type", "Unknown")
                user_info = enrollment.get("user", {})
                user_id = user_info.get("id")
                user_email = user_info.get("login_id", user_info.get("email", "Unknown"))
                user_name = user_info.get("name", "Unknown")

                # Check if this is the admin user
                if user_id == admin_id:
                    logger.info(f"Found admin user {user_name} ({user_email}) enrolled as {enrollment_type}")
                    print(f"🔍 Found admin user {user_name} ({user_email}) enrolled as {enrollment_type}")
                    admin_removed = True

                logger.info(f"Removing {enrollment_type} enrollment for {user_name} ({user_email})")

                if await self.remove_enrollment(course_id, enrollment_id, user_email):
                    success_count += 1
                else:
                    logger.error(f"Failed to remove enrollment for {user_email}")

            if admin_removed:
                print(f"✅ Successfully removed admin from course {course_name}")

            if success_count == len(enrollments):
                logger.info(f"Successfully removed all {len(enrollments)} enrollments from course {course_name}")
                print(f"✅ Successfully removed all {len(enrollments)} enrollments from course {course_name}")
                return True
            else:
                logger.warning(f"Removed {success_count}/{len(enrollments)} enrollments from course {course_name}")
                print(f"⚠️ Removed {success_count}/{len(enrollments)} enrollments from course {course_name}")
                return success_count > 0  # Partial success

        except Exception as e:
            logger.error(f"Error removing enrollments from course {course_name}: {e}")
            print(f"💥 Error removing enrollments from course {course_name}: {e}")
            return False

    async def get_course_assignments(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all assignments in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments"
                params = {"per_page": "100"}

                async with session.get(url, headers=self.headers, params=params) as response:
                    if 200 == response.status:
                        assignments = await response.json()
                        logger.info(f"Found {len(assignments)} assignments in course {course_id}")
                        return assignments
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get assignments for course {course_id}: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error getting assignments for course {course_id}: {e}")
            return []

    async def delete_assignment(self, course_id: str, assignment_id: str) -> bool:
        """Delete a specific assignment"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}"

                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Deleted assignment {assignment_id} from course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to delete assignment {assignment_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting assignment {assignment_id}: {e}")
            return False

    async def delete_all_assignments(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all assignments from a course"""
        try:
            assignments = await self.get_course_assignments(course_id)

            if not assignments:
                logger.info(f"No assignments found in course {course_name}")
                return True

            logger.info(f"Deleting {len(assignments)} assignments from course {course_name}")
            print(f"🗑️ Deleting {len(assignments)} existing assignments from course {course_name}")

            success_count = 0
            for assignment in assignments:
                assignment_id = str(assignment.get("id", ""))
                if await self.delete_assignment(course_id, assignment_id):
                    success_count += 1

            if success_count == len(assignments):
                print(f"✅ Successfully deleted all assignments from course {course_name}")
                return True
            else:
                print(f"⚠️ Deleted {success_count}/{len(assignments)} assignments from course {course_name}")
                return success_count > 0

        except Exception as e:
            logger.error(f"Error deleting assignments from course {course_name}: {e}")
            return False

    async def get_course_modules(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all modules in a course"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/modules"
                params = {"per_page": "100"}

                async with session.get(url, headers=self.headers, params=params) as response:
                    if 200 == response.status:
                        modules = await response.json()
                        logger.info(f"Found {len(modules)} modules in course {course_id}")
                        return modules
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get modules for course {course_id}: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error getting modules for course {course_id}: {e}")
            return []

    async def delete_module(self, course_id: str, module_id: str) -> bool:
        """Delete a specific module"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/modules/{module_id}"

                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Deleted module {module_id} from course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to delete module {module_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting module {module_id}: {e}")
            return False

    async def delete_all_modules(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all modules from a course"""
        try:
            modules = await self.get_course_modules(course_id)

            if not modules:
                logger.info(f"No modules found in course {course_name}")
                return True

            logger.info(f"Deleting {len(modules)} modules from course {course_name}")
            print(f"🗑️ Deleting {len(modules)} existing modules from course {course_name}")

            success_count = 0
            for module in modules:
                module_id = str(module.get("id", ""))
                if await self.delete_module(course_id, module_id):
                    success_count += 1

            if success_count == len(modules):
                print(f"✅ Successfully deleted all modules from course {course_name}")
                return True
            else:
                print(f"⚠️ Deleted {success_count}/{len(modules)} modules from course {course_name}")
                return success_count > 0

        except Exception as e:
            logger.error(f"Error deleting modules from course {course_name}: {e}")
            return False

    async def get_course_discussion_topics(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all discussion topics in a course (non-announcements)"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics"
                params = {"per_page": "100"}

                async with session.get(url, headers=self.headers, params=params) as response:
                    if 200 == response.status:
                        topics = await response.json()
                        # Filter out announcements
                        discussions = [t for t in topics if not t.get("is_announcement", False)]
                        logger.info(f"Found {len(discussions)} discussion topics in course {course_id}")
                        return discussions
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get discussion topics for course {course_id}: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error getting discussion topics for course {course_id}: {e}")
            return []

    async def delete_discussion_topic(self, course_id: str, topic_id: str) -> bool:
        """Delete a specific discussion topic"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics/{topic_id}"

                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Deleted discussion topic {topic_id} from course {course_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to delete discussion topic {topic_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting discussion topic {topic_id}: {e}")
            return False

    async def delete_all_discussion_topics(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all discussion topics from a course"""
        try:
            topics = await self.get_course_discussion_topics(course_id)

            if not topics:
                logger.info(f"No discussion topics found in course {course_name}")
                return True

            logger.info(f"Deleting {len(topics)} discussion topics from course {course_name}")
            print(f"🗑️ Deleting {len(topics)} existing discussion topics from course {course_name}")

            success_count = 0
            for topic in topics:
                topic_id = str(topic.get("id", ""))
                if await self.delete_discussion_topic(course_id, topic_id):
                    success_count += 1

            if success_count == len(topics):
                print(f"✅ Successfully deleted all discussion topics from course {course_name}")
                return True
            else:
                print(f"⚠️ Deleted {success_count}/{len(topics)} discussion topics from course {course_name}")
                return success_count > 0

        except Exception as e:
            logger.error(f"Error deleting discussion topics from course {course_name}: {e}")
            return False

    async def reset_course_homepage(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Reset course homepage to default"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/courses/{course_id}"
                data = {
                    "course": {
                        "default_view": "modules",  # Set to modules view
                        "syllabus_body": "",  # Clear syllabus
                        "public_description": ""  # Clear public description
                    }
                }

                async with session.put(url, headers=self.headers, json=data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Reset homepage for course {course_name}")
                        print(f"✅ Reset homepage and syllabus for course {course_name}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to reset homepage for course {course_name}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error resetting homepage for course {course_name}: {e}")
            return False

    async def clean_all_course_content(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Clean all content from a course (enrollments, assignments, modules, discussions, etc.)"""
        try:
            print(f"🧹 Starting complete cleanup for course {course_name}")

            # Track overall success
            all_success = True

            # 1. Remove all enrollments (including admin if auto-enrolled)
            if not await self.remove_all_enrollments(course_id, course_name):
                all_success = False

            # 2. Delete all assignments
            if not await self.delete_all_assignments(course_id, course_name):
                all_success = False

            # 3. Delete all modules
            if not await self.delete_all_modules(course_id, course_name):
                all_success = False

            # 4. Delete all discussion topics
            if not await self.delete_all_discussion_topics(course_id, course_name):
                all_success = False

            # 5. Delete all announcements
            if not await self.delete_all_announcements(course_id, course_name):
                all_success = False

            # 6. Reset homepage and syllabus
            if not await self.reset_course_homepage(course_id, course_name):
                all_success = False

            if all_success:
                print(f"✅ Successfully cleaned all content from course {course_name}")
            else:
                print(f"⚠️ Some content cleanup failed for course {course_name}")

            return all_success

        except Exception as e:
            logger.error(f"Error cleaning course content for {course_name}: {e}")
            print(f"💥 Error cleaning course content for {course_name}: {e}")
            return False

    async def publish_course(self, course_id: str, course_name: str) -> bool:
        """Publish a course to make it visible to students using app_specific module"""
        try:
            success = self.canvas_api.publish_course(int(course_id))
            if success:
                logger.info(f"Published course: {course_name} (ID: {course_id})")
                return True
            else:
                logger.error(f"Failed to publish course {course_name}")
                return False
        except Exception as e:
            logger.error(f"Error publishing course {course_name}: {e}")
            return False

    async def get_course_status(self, course_id: str) -> Optional[str]:
        """Get the current workflow state of a course using app_specific module"""
        try:
            course = self.canvas_api.get_course(int(course_id))
            if course:
                workflow_state = course.get("workflow_state", "unknown")
                logger.info(f"Course {course_id} status: {workflow_state}")
                return workflow_state
            else:
                logger.error(f"Failed to get course status for {course_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting course status for {course_id}: {e}")
            return None
    
    async def publish_all_courses(self) -> bool:
        """Publish all unpublished courses in the system"""
        try:
            logger.info("Starting to publish all unpublished courses...")
            
            # Get all courses
            courses = await self.get_all_courses()
            if not courses:
                logger.info("No courses found to publish")
                return True
            
            # Filter unpublished courses
            unpublished_courses = []
            for course in courses:
                course_id = str(course.get("id", ""))
                course_name = course.get("name", "Unknown")
                workflow_state = course.get("workflow_state", "unknown")
                
                if workflow_state != "available":
                    unpublished_courses.append({
                        "id": course_id,
                        "name": course_name
                    })
            
            if not unpublished_courses:
                logger.info("All courses are already published")
                return True
            
            logger.info(f"Found {len(unpublished_courses)} unpublished courses to publish")
            
            # Publish each unpublished course
            success_count = 0
            for course in unpublished_courses:
                if await self.publish_course(course["id"], course["name"]):
                    success_count += 1
                else:
                    logger.error(f"Failed to publish course: {course['name']}")
            
            # Print summary
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"COURSE PUBLICATION COMPLETED - {timestamp}")
            print(f"{'='*60}")
            print(f"Total unpublished courses: {len(unpublished_courses)}")
            print(f"Successfully published: {success_count}")
            print(f"Failed: {len(unpublished_courses) - success_count}")
            print(f"{'='*60}")
            
            if success_count == len(unpublished_courses):
                print("✅ All courses published successfully!")
            else:
                print("⚠️  Some courses failed to publish. Check logs for details.")
            
            return success_count == len(unpublished_courses)
            
        except Exception as e:
            logger.error(f"Fatal error during course publication: {e}")
            return False
    
    async def setup_course(self, course_info: Dict[str, Any]) -> bool:
        """Set up a complete course with announcements and enrollments"""
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
                print(f"📚 Setting up existing course: {course_info['name']} (ID: {course_id})")
            else:
                logger.info(f"Setting up new course: {course_info['name']} (ID: {course_id})")
                print(f"✨ Setting up new course: {course_info['name']} (ID: {course_id})")

            # 2. Clean all existing course content (enrollments, assignments, modules, discussions, etc.)
            content_cleaned = await self.clean_all_course_content(course_id, course_info["name"])
            if not content_cleaned:
                logger.warning(f"Failed to clean some existing content for {course_info['name']}")
                print(f"⚠️ Failed to clean some existing content for {course_info['name']}, but continuing...")
            else:
                logger.info(f"Successfully cleaned all content for {course_info['name']}")
                print(f"✅ Successfully cleaned all content for {course_info['name']}")

            # 3. Enroll teacher (if specified)
            teacher_enrolled = False
            if "teacher" in course_info and course_info["teacher"]:
                teacher_enrolled = await self.enroll_teacher(course_id, course_info["teacher"])
                if not teacher_enrolled:
                    logger.warning(f"Failed to enroll teacher for {course_info['name']}")
                    print(f"⚠️ Failed to enroll teacher for {course_info['name']}")
                else:
                    logger.info(f"Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")
                    print(f"👨‍🏫 Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")

            # 4. Create multiple announcements (main exam announcement + additional realistic announcements)
            announcements_created = await self.create_multiple_announcements(course_id, course_info)
            if not announcements_created:
                logger.warning(f"Failed to create announcements for {course_info['name']}")
                print(f"⚠️ Failed to create announcements for {course_info['name']}")
            else:
                logger.info(f"Successfully created announcements for {course_info['name']}")
                print(f"🎉 Successfully created multiple announcements for {course_info['name']}")

            # 5. Enroll students
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
            print(f"👥 Successfully enrolled {enrollment_success}/{len(students_to_enroll)} students in {course_info['name']}")

            # 6. Publish course (for all courses)
            course_published = await self.publish_course(course_id, course_info["name"])
            if not course_published:
                logger.warning(f"Failed to publish course {course_info['name']}")
                print(f"⚠️ Failed to publish course {course_info['name']}")
            else:
                logger.info(f"Successfully published course {course_info['name']}")
                print(f"🌟 Successfully published course {course_info['name']}")

            return True

        except Exception as e:
            logger.error(f"Error setting up course {course_info['name']}: {e}")
            print(f"💥 Error setting up course {course_info['name']}: {e}")
            return False
    
    async def run_setup(self):
        """Run the complete course setup process"""
        try:
            logger.info("Starting Canvas course setup...")
            
            # Load data
            if not self.load_data():
                return False
            
            # Get current user profile to verify authentication
            logger.info("Getting current user profile...")
            user_profile = await self.get_current_user_profile()
            if user_profile:
                logger.info(f"Authenticated as: {user_profile.get('name', 'Unknown user')} ({user_profile.get('email', 'No email')})")
            else:
                logger.warning("Could not retrieve user profile, but continuing with course setup...")
            
            # Process each course
            success_count = 0
            total_courses = len(self.courses_data["courses"])
            
            for course_info in self.courses_data["courses"]:
                if await self.setup_course(course_info):
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
                # Step 1: First conclude the course (required before deletion)
                conclude_url = f"{self.base_url}/api/v1/courses/{course_id}"
                conclude_data = {"event": "conclude"}
                
                async with session.put(conclude_url, headers=self.headers, json=conclude_data) as response:
                    if 200 == response.status:
                        conclude_response = await response.json()
                        current_state = conclude_response.get('workflow_state', 'unknown')
                        logger.info(f"Concluded course: {course_name} (ID: {course_id}) - State: {current_state}")
                        print(f"✅ Concluded course: {course_name} (ID: {course_id}) - State: {current_state}")
                    else:
                        logger.warning(f"Failed to conclude course {course_name}: {response.status}")
                        print(f"⚠️ Failed to conclude course {course_name}: {response.status}")
                
                # Wait for conclude operation to complete
                await asyncio.sleep(1.5)
                
                # Step 2: Try multiple deletion approaches
                deletion_methods = [
                    # Method 1: Standard event-based deletion
                    {"url": f"{self.base_url}/api/v1/courses/{course_id}", "data": {"event": "delete"}, "name": "Event Delete"},
                    # Method 2: Course parameter deletion  
                    {"url": f"{self.base_url}/api/v1/courses/{course_id}", "data": {"course": {"event": "delete"}}, "name": "Course Event Delete"},
                    # Method 3: Direct workflow state change
                    {"url": f"{self.base_url}/api/v1/courses/{course_id}", "data": {"course": {"workflow_state": "deleted"}}, "name": "Workflow State Delete"},
                ]
                
                for method in deletion_methods:
                    print(f"🔄 Trying {method['name']} for course: {course_name} (ID: {course_id})")
                    print(f"self.headers: {self.headers}")
                    print(f"method['url']: {method['url']}")
                    print(f"method['data']: {method['data']}")
                    
                    async with session.put(method["url"], headers=self.headers, json=method["data"]) as response:
                        if 200 == response.status:
                            # Check response body to confirm deletion
                            response_data = await response.json()
                            response_state = response_data.get('workflow_state', 'unknown')
                            print(f"🔍 {method['name']} response state: {response_state}")
                            
                            # Wait and verify deletion
                            await asyncio.sleep(1)
                            verify_status = await self.get_course_status(course_id)
                            print(f"📊 Course status after {method['name']}: {verify_status}")
                            
                            if verify_status in ["deleted", "completed"] or verify_status is None:
                                logger.info(f"Successfully deleted course using {method['name']}: {course_name} (ID: {course_id})")
                                print(f"🗑️ Successfully deleted course using {method['name']}: {course_name} (ID: {course_id}) - Final Status: {verify_status}")
                                return True
                            elif response_state in ["deleted", "completed"]:
                                # Response shows deleted but verification might have issues
                                logger.info(f"Course appears deleted via {method['name']}: {course_name} (ID: {course_id})")
                                print(f"🗑️ Course appears deleted via {method['name']}: {course_name} (ID: {course_id}) - Response State: {response_state}")
                                return True
                        else:
                            error_text = await response.text()
                            print(f"❌ {method['name']} failed: {response.status} - {error_text}")
                    
                    # Small delay between methods
                    await asyncio.sleep(0.5)
                
                # Step 3: Final fallback - try to make course invisible
                logger.info(f"All deletion methods failed, trying final deactivation: {course_name} (ID: {course_id})")
                print(f"🔄 Final attempt - deactivating course: {course_name} (ID: {course_id})")
                deactivate_url = f"{self.base_url}/api/v1/courses/{course_id}"
                deactivate_data = {"course": {"workflow_state": "completed"}}
                
                async with session.put(deactivate_url, headers=self.headers, json=deactivate_data) as response:
                    if 200 == response.status:
                        # Check response body and verify status
                        deactivate_response = await response.json()
                        print(f"🔍 Deactivate response body: {deactivate_response}")
                        
                        # Verify deactivation
                        await asyncio.sleep(0.5)
                        final_status = await self.get_course_status(course_id)
                        print(f"📊 Final course status: {final_status}")
                        
                        if final_status in ["deleted", "completed"]:
                            logger.info(f"Deactivated course: {course_name} (ID: {course_id})")
                            print(f"✅ Deactivated course: {course_name} (ID: {course_id}) - Status: {final_status}")
                            return True
                        else:
                            logger.error(f"Deactivation failed - course still has status: {final_status}")
                            print(f"❌ Deactivation failed - course still has status: {final_status}")
                            return False
                    else:
                        deactivate_error = await response.text()
                        logger.error(f"Failed to deactivate course {course_name}: {response.status} - {deactivate_error}")
                        print(f"❌ Failed to deactivate course {course_name}: {response.status} - {deactivate_error}")
                        return False
        except Exception as e:
            logger.error(f"Error deleting course {course_name}: {e}")
            print(f"💥 Error deleting course {course_name}: {e}")
            return False
    
    async def delete_all_courses(self) -> bool:
        """Delete all courses from Canvas using app_specific module"""
        try:
            logger.info("Starting deletion of all courses...")

            # Get all courses using app_specific module
            courses = self.canvas_api.list_courses(include_deleted=False, account_id=1)

            if not courses:
                logger.info("No courses found to delete")
                return True

            # Filter out system courses (usually have specific IDs or names)
            courses_to_delete = []
            for course in courses:
                course_id = str(course.get("id", ""))
                course_name = course.get("name", "Unknown")

                courses_to_delete.append({
                    "id": course_id,
                    "name": course_name
                })

            if not courses_to_delete:
                logger.info("No user-created courses found to delete")
                return True

            logger.info(f"Deleting {len(courses_to_delete)} courses...")
            print(f"🗑️ Deleting {len(courses_to_delete)} courses...")

            deleted_count = 0
            for course in courses_to_delete:
                course_id = course["id"]
                course_name = course["name"]

                # Use app_specific module to delete course
                success = self.canvas_api.delete_course(int(course_id), event='delete')
                if success:
                    deleted_count += 1
                    logger.info(f"Deleted course: {course_name} (ID: {course_id})")
                    print(f"✅ Deleted course: {course_name} (ID: {course_id})")
                else:
                    logger.error(f"Failed to delete course: {course_name} (ID: {course_id})")
                    print(f"❌ Failed to delete course: {course_name} (ID: {course_id})")

            logger.info(f"Deleted {deleted_count}/{len(courses_to_delete)} courses")
            print(f"📊 Deleted {deleted_count}/{len(courses_to_delete)} courses")
            return deleted_count == len(courses_to_delete)

        except Exception as e:
            logger.error(f"Error deleting all courses: {e}")
            print(f"💥 Error deleting all courses: {e}")
            return False

    async def setup_courses(self, agent_workspace=None) -> bool:
        """Main method to set up all courses with students and announcements"""
        try:
            # Implementation will be similar to run_setup method
            # This is called from main function
            return await self.run_setup(agent_workspace)
        except Exception as e:
            logger.error(f"Fatal error during course setup: {e}")
            return False

async def run_with_args(delete=False, publish=False, agent_workspace=None):
    """Run the setup with specified arguments"""
    setup = CanvasCourseSetup()
    
    if delete:
        print("🗑️  Running in DELETE mode - will delete all courses")
        success = await setup.delete_all_courses()
        if success:
            print("\n🎉 Course deletion completed successfully!")
        else:
            print("\n❌ Course deletion encountered errors. Check logs for details.")
    elif publish:
        print("📢 Running in PUBLISH mode - will publish all unpublished courses")
        success = await setup.publish_all_courses()
        if success:
            print("\n🎉 Course publication completed successfully!")
        else:
            print("\n❌ Course publication encountered errors. Check logs for details.")
    else:
        print("🚀 Running in SETUP mode - will create courses")
        success = await setup.run_setup()
        if success:
            print("\n🎉 Course setup completed successfully!")
        else:
            print("\n❌ Course setup encountered errors. Check logs for details.")

async def main(delete=False, publish=False, agent_workspace=None):
    """Main function that can accept external arguments"""
    # If no parameters are passed, parse from command line
    if delete is False and publish is False and agent_workspace is None:
        import argparse
        
        # Create parameter parser
        parser = argparse.ArgumentParser(description='Canvas Course Setup Tool')
        parser.add_argument('--delete', action='store_true', help='Delete all courses')
        parser.add_argument('--publish', action='store_true', help='Publish all unpublished courses')
        parser.add_argument('--agent_workspace', help='Agent workspace path')
        
        # Parse parameters
        args = parser.parse_args()
        delete = args.delete
        publish = args.publish
        agent_workspace = args.agent_workspace
    
    # Call run_with_args function
    await run_with_args(delete=delete, publish=publish, agent_workspace=agent_workspace)

if __name__ == "__main__":
    asyncio.run(main())
