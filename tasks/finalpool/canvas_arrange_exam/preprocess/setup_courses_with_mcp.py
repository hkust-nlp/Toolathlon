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

os.environ["TESSDATA_PREFIX"] = "/ssddata/wzengak/mcp_bench/mcpbench_dev/scripts"

# Import Canvas configuration
import sys
import os
from pathlib import Path

# Add parent directory to path to ensure we can import token_key_session
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from token_key_session import all_token_key_session

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
    
    def generate_additional_announcements(self, course_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate additional realistic announcements for a course"""
        course_name = course_info["name"]
        course_code = course_info["course_code"]
        
        # 基础公告模板
        announcements = []
        
        # 1. 课程开始欢迎公告
        # 构建考试类型信息
        exam_type = course_info.get("exam_type", "TBD")
        if exam_type == "no_exam":
            exam_type_display = "No Final Exam"
        else:
            exam_type_display = exam_type.replace("_", " ").title()
        
        # 构建学分信息
        credits = course_info.get("credits", "TBD")
        
        announcements.append({
            "title": f"Welcome to {course_code}!",
            "content": f"Dear {course_code} students,\n\nWelcome to {course_name}! I'm excited to have you in this course.\n\n🏫 Course Information:\n🎓 Credits: {credits}\n📝 Exam Type: {exam_type_display}\n\n📚 Course Materials:\n- Please check the syllabus for required textbooks\n- All lecture slides will be posted on Canvas\n- Office hours: Tuesdays and Thursdays 2:00-4:00 PM\n\n💡 Important Notes:\n- Please introduce yourself in the discussion forum\n- Check your email regularly for course updates\n- Don't hesitate to ask questions!\n\nLooking forward to a great semester!\n\nBest regards,\nCourse Instructor"
        })
        
        # 2. 第一次作业公告 (10月)
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
        
        # 3. 期中考试或测验公告 (11月)
        if course_info.get("exam_type") != "no_exam":
            announcements.append({
                "title": f"Midterm Exam Information - {course_code}",
                "content": f"Dear {course_code} students,\n\n📅 Midterm Exam Schedule:\n\n📅 Date: November 12, 2024\n⏰ Time: Regular class time\n⏱️ Duration: 75 minutes\n📍 Location: Regular classroom\n\n📚 Exam Coverage:\n- Chapters 1-6 from textbook\n- All lecture materials through Week 8\n- Homework assignments 1-4\n\n📝 Format:\n- Multiple choice (40%)\n- Short answer questions (35%)\n- Problem solving (25%)\n\n💡 Study Tips:\n- Review lecture slides and notes\n- Practice problems from homework\n- Attend review session on November 10\n\nGood luck with your preparation!\n\nBest regards,\nCourse Instructor"
            })
        
        # 4. 项目公告（针对编程类课程）(12月)
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
        
        # # 5. 重要通知公告 (期末准备期 - 12月初)
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
            # 1. 先创建早期的学期公告 (9月-12月，按时间顺序)
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
                
                # 小间隔，避免API调用过于频繁
                await asyncio.sleep(0.3)
            
            # 2. 最后创建期末考试公告 (1月 2025)
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
            
            return success_count > 0  # 至少成功创建一个公告就算成功
            
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
        """Delete a specific announcement using multiple methods"""
        try:
            async with aiohttp.ClientSession() as session:
                # Method 1: First try to unpublish the announcement
                url = f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics/{announcement_id}"
                unpublish_data = {
                    "published": False
                }
                
                logger.info(f"Step 1: Unpublishing announcement {announcement_title} (ID: {announcement_id})")
                print(f"🔄 Step 1: Unpublishing announcement '{announcement_title}' (ID: {announcement_id})")
                async with session.put(url, headers=self.headers, json=unpublish_data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Successfully unpublished announcement: {announcement_title}")
                        print(f"✅ Step 1 SUCCESS: Unpublished announcement '{announcement_title}'")
                    else:
                        logger.warning(f"Failed to unpublish announcement {announcement_title}: {response.status}")
                        print(f"❌ Step 1 FAILED: Could not unpublish '{announcement_title}' - Status: {response.status}")
                
                # Wait a moment for the unpublish to take effect
                await asyncio.sleep(0.5)
                
                # Method 2: Try direct DELETE request
                logger.info(f"Step 2: Attempting direct DELETE for announcement {announcement_title}")
                print(f"🔄 Step 2: Attempting direct DELETE for announcement '{announcement_title}'")
                async with session.delete(url, headers=self.headers) as response:
                    if 200 <= response.status < 300:
                        print(f"✅ Step 2: DELETE request returned success status {response.status}")
                        # Verify deletion by trying to get the announcement
                        await asyncio.sleep(0.5)
                        print(f"🔍 Step 2: Verifying deletion by checking if announcement still exists...")
                        async with session.get(url, headers=self.headers) as verify_response:
                            if verify_response.status == 404:
                                logger.info(f"Successfully deleted announcement: {announcement_title} (ID: {announcement_id})")
                                print(f"🎉 Step 2 COMPLETE SUCCESS: Announcement '{announcement_title}' was fully deleted! (Method: Direct DELETE)")
                                return True
                            else:
                                logger.warning(f"DELETE returned success but announcement still exists: {announcement_title}")
                                print(f"⚠️ Step 2 PARTIAL: DELETE returned success but announcement '{announcement_title}' still exists (Status: {verify_response.status})")
                    else:
                        logger.warning(f"Direct DELETE failed for {announcement_title}: {response.status}")
                        print(f"❌ Step 2 FAILED: Direct DELETE failed for '{announcement_title}' - Status: {response.status}")
                
                # Method 3: Try changing workflow_state to deleted
                logger.info(f"Step 3: Attempting workflow_state change for announcement {announcement_title}")
                print(f"🔄 Step 3: Attempting workflow_state='deleted' for announcement '{announcement_title}'")
                workflow_data = {
                    "workflow_state": "deleted"
                }
                
                async with session.put(url, headers=self.headers, json=workflow_data) as response:
                    if 200 <= response.status < 300:
                        print(f"✅ Step 3: Workflow state change returned success status {response.status}")
                        # Verify deletion
                        await asyncio.sleep(0.5)
                        print(f"🔍 Step 3: Verifying workflow_state deletion...")
                        async with session.get(url, headers=self.headers) as verify_response:
                            if verify_response.status == 404:
                                logger.info(f"Successfully deleted announcement via workflow_state: {announcement_title} (ID: {announcement_id})")
                                print(f"🎉 Step 3 COMPLETE SUCCESS: Announcement '{announcement_title}' was fully deleted! (Method: Workflow State)")
                                return True
                            else:
                                response_data = await verify_response.json()
                                current_state = response_data.get('workflow_state', 'unknown')
                                print(f"🔍 Step 3: Current workflow_state: {current_state}")
                                if current_state == 'deleted':
                                    logger.info(f"Successfully marked announcement as deleted: {announcement_title} (ID: {announcement_id})")
                                    print(f"🎉 Step 3 SUCCESS: Announcement '{announcement_title}' marked as deleted! (Method: Workflow State)")
                                    return True
                                else:
                                    print(f"⚠️ Step 3 PARTIAL: Workflow state is '{current_state}', not 'deleted'")
                    else:
                        logger.warning(f"Workflow state change failed for {announcement_title}: {response.status}")
                        print(f"❌ Step 3 FAILED: Workflow state change failed for '{announcement_title}' - Status: {response.status}")
                
                # Method 4: Final fallback - mark as unpublished and try to hide it
                logger.info(f"Step 4: Final fallback - marking as unpublished for announcement {announcement_title}")
                print(f"🔄 Step 4: Final fallback - hiding announcement '{announcement_title}' (unpublish + lock + rename)")
                fallback_data = {
                    "published": False,
                    "locked": True,
                    "title": f"[DELETED] {announcement_title}"
                }
                
                async with session.put(url, headers=self.headers, json=fallback_data) as response:
                    if 200 <= response.status < 300:
                        logger.warning(f"Could not delete announcement, marked as unpublished instead: {announcement_title}")
                        print(f"⚠️ Step 4 FALLBACK SUCCESS: Could not delete '{announcement_title}', but successfully hid it from students")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"All deletion methods failed for announcement {announcement_title}: {response.status} - {error_text}")
                        print(f"💥 Step 4 FAILED: All deletion methods failed for '{announcement_title}' - Status: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error deleting announcement {announcement_title}: {e}")
            return False
    
    async def delete_all_announcements(self, course_id: str, course_name: str = "Unknown") -> bool:
        """Delete all announcements in a course"""
        try:
            # Get all announcements
            announcements = await self.get_course_announcements(course_id)
            
            if not announcements:
                logger.info(f"No announcements found in course {course_name} (ID: {course_id})")
                return True
            
            logger.info(f"Deleting {len(announcements)} announcements from course {course_name} (ID: {course_id})")
            print(f"🗑️ Deleting {len(announcements)} existing announcements from course {course_name}")
            
            # Delete each announcement
            success_count = 0
            for announcement in announcements:
                announcement_id = str(announcement.get("id", ""))
                announcement_title = announcement.get("title", "Unknown")
                
                if await self.delete_announcement(course_id, announcement_id, announcement_title):
                    success_count += 1
                else:
                    logger.error(f"Failed to delete announcement: {announcement_title}")
            
            if success_count == len(announcements):
                logger.info(f"Successfully deleted all {len(announcements)} announcements from course {course_name}")
                print(f"✅ Successfully deleted all {len(announcements)} announcements from course {course_name}")
                return True
            else:
                logger.warning(f"Deleted {success_count}/{len(announcements)} announcements from course {course_name}")
                print(f"⚠️ Deleted {success_count}/{len(announcements)} announcements from course {course_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting announcements from course {course_name}: {e}")
            print(f"💥 Error deleting announcements from course {course_name}: {e}")
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
            
            # 2. Enroll teacher (if specified)
            teacher_enrolled = False
            if "teacher" in course_info and course_info["teacher"]:
                teacher_enrolled = await self.enroll_teacher(course_id, course_info["teacher"])
                if not teacher_enrolled:
                    logger.warning(f"Failed to enroll teacher for {course_info['name']}")
                    print(f"⚠️ Failed to enroll teacher for {course_info['name']}")
                else:
                    logger.info(f"Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")
                    print(f"👨‍🏫 Successfully enrolled teacher {course_info['teacher']} in {course_info['name']}")
            
            # 3. Delete existing announcements before creating new ones
            announcements_deleted = await self.delete_all_announcements(course_id, course_info["name"])
            if not announcements_deleted:
                logger.warning(f"Failed to delete some existing announcements for {course_info['name']}")
            
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
        """Delete all courses from Canvas"""
        try:
            logger.info("Starting deletion of all courses...")
            
            # Get all courses
            courses = await self.get_all_courses()
            #print(f"courses: {courses}")
            if not courses:
                #print(f"courses: {courses}")
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

            #print(f"courses_to_delete: {courses_to_delete}")
            
            logger.info(f"Found {len(courses_to_delete)} courses to delete")
            
            # Delete each course
            success_count = 0
            for course in courses_to_delete:
                if await self.delete_course(course["id"], course["name"]):
                    success_count += 1
                else:
                    print(f"Failed to delete course: {course['name']}")
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
                print(f"success_count: {success_count}")
                print(f"len(courses_to_delete): {len(courses_to_delete)}")
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
