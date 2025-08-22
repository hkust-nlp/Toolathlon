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

os.environ["TESSDATA_PREFIX"] = "/ssddata/xiaochen/workspace/mcpbench_dev/scripts"

# Import Canvas configuration
from tasks.xiaochen.canvas_arrange_exam.token_key_session import all_token_key_session
CANVAS_API_TOKEN = all_token_key_session.admin_canvas_token
CANVAS_DOMAIN = all_token_key_session.canvas_domain
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
            # Load course configuration
            with open('tasks/xiaochen/canvas_arrange_exam/files/course_config.json', 'r') as f:
                self.courses_data = json.load(f)
            
            # Load users data
            with open('tasks/xiaochen/canvas_arrange_exam/files/canvas_users.json', 'r') as f:
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
            else:
                logger.info(f"Setting up new course: {course_info['name']} (ID: {course_id})")
            
            # 2. Enroll teacher (if specified)
            teacher_enrolled = False
            if "teacher" in course_info and course_info["teacher"]:
                teacher_enrolled = await self.enroll_teacher(course_id, course_info["teacher"])
                if not teacher_enrolled:
                    logger.warning(f"Failed to enroll teacher for {course_info['name']}")
                else:
                    logger.info(f"Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")
            
            # 3. Create announcement 
            
            announcement_created = await self.create_announcement(course_id, course_info["announcement"])
            if not announcement_created:
                logger.warning(f"Failed to create announcement for {course_info['name']}")
            else:
                logger.info(f"Successfully created announcement for {course_info['name']}")
            
            
            # 4. Enroll students
            students_to_enroll = course_info["students"].copy()
            
            # Remove excluded students if any
            if "exclude_students" in course_info:
                for excluded_email in course_info["exclude_students"]:
                    if excluded_email in students_to_enroll:
                        students_to_enroll.remove(excluded_email)
                        logger.info(f"Excluded {excluded_email} from {course_info['name']}")
            
            # Enroll each student
            enrollment_success = 0
            for student_email in students_to_enroll:
                if await self.enroll_student(course_id, student_email):
                    enrollment_success += 1
            
            logger.info(f"Successfully enrolled {enrollment_success}/{len(students_to_enroll)} students in {course_info['name']}")
            
            # 5. Publish course (for all courses)
            course_published = await self.publish_course(course_id, course_info["name"])
            if not course_published:
                logger.warning(f"Failed to publish course {course_info['name']}")
            else:
                logger.info(f"Successfully published course {course_info['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up course {course_info['name']}: {e}")
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
    
    async def delete_all_courses(self) -> bool:
        """Delete all courses from Canvas"""
        try:
            logger.info("Starting deletion of all courses...")
            
            # Get all courses
            courses = await self.get_all_courses()
            if not courses:
                logger.info("No courses found to delete")
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
                return True
            
            logger.info(f"Found {len(courses_to_delete)} courses to delete")
            
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
    # 如果没有传入参数，则从命令行解析
    if delete is False and publish is False and agent_workspace is None:
        import argparse
        
        # 创建参数解析器
        parser = argparse.ArgumentParser(description='Canvas Course Setup Tool')
        parser.add_argument('--delete', action='store_true', help='Delete all courses')
        parser.add_argument('--publish', action='store_true', help='Publish all unpublished courses')
        parser.add_argument('--agent_workspace', help='Agent workspace path')
        
        # 解析参数
        args = parser.parse_args()
        delete = args.delete
        publish = args.publish
        agent_workspace = args.agent_workspace
    
    # 调用run_with_args函数
    await run_with_args(delete=delete, publish=publish, agent_workspace=agent_workspace)

if __name__ == "__main__":
    asyncio.run(main())
