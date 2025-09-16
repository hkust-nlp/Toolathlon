#!/usr/bin/env python3
"""
Canvas Course Preprocessing Pipeline

This script creates the initial course setup for the Canvas notification task:
1. Creates "Introduction to AI" course
2. Enrolls specific students (1st, 3rd, 5th, 10th, 15th from CSV)
3. Adds current user as teacher
4. Creates assignments from markdown files

Based on the task requirements in tasks/yuzhen/canvas_notification/
"""

import sys
import csv
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path to import canvas_api and token config
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

try:
    from canvas_api import CanvasAPI
    from other_key import all_token_key_session, teacher_email
except ImportError as e:
    print(f"❌ Error: Cannot import required modules: {e}")
    print("Make sure canvas_api.py and other_key.py are in the parent directory.")
    sys.exit(1)


class CanvasPreprocessPipeline:
    """Pipeline for setting up Canvas course with specific requirements"""
    
    def __init__(self, canvas_url: str = None, 
                 canvas_token: str = None,
                 agent_workspace: str = None):
        """
        Initialize the preprocessing pipeline
        
        Args:
            canvas_url: Canvas base URL (defaults to config file)
            canvas_token: Canvas API access token (defaults to config file)
            agent_workspace: Agent workspace directory (for compatibility)
        """
        # Use config file values if not provided
        if canvas_url is None:
            canvas_url = f"http://{all_token_key_session.canvas_admin_domain}"
        if canvas_token is None:
            canvas_token = all_token_key_session.canvas_admin_api_token
            
        self.canvas = CanvasAPI(canvas_url, canvas_token)
        self.course_id = None
        self.course_name = "Art History"
        self.course_code = "AH101"
        self.agent_workspace = agent_workspace
        
        # File paths relative to current directory
        current_dir = Path(__file__).parent
        self.student_csv = current_dir / "student_list.csv"
        self.assignments_dir = current_dir / "assignments"
        
        # Target student indices
        self.target_student_indices = [1, 2, 3, 4, 5, 6]
    
    def load_target_students(self) -> List[Tuple[str, str]]:
        """
        Load specific students from CSV file based on target indices
        
        Returns:
            List of (name, email) tuples for target students
        """
        target_students = []
        
        try:
            with open(self.student_csv, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                students_list = list(reader)
                
                print(f"📚 Loaded {len(students_list)} total students from CSV")
                print(f"🎯 Selecting students at positions: {self.target_student_indices}")
                
                for index in self.target_student_indices:
                    if 1 <= index <= len(students_list):
                        student = students_list[index - 1]  # Convert to 0-based index
                        name = student.get('Name', '').strip()
                        email = student.get('email', '').strip()
                        
                        if name and email:
                            target_students.append((name, email))
                            print(f"   Position {index}: {name} ({email})")
                        else:
                            print(f"   ⚠️  Position {index}: Invalid data {student}")
                    else:
                        print(f"   ❌ Position {index}: Out of range (max: {len(students_list)})")
                
        except FileNotFoundError:
            print(f"❌ Error: Student CSV file not found: {self.student_csv}")
        except Exception as e:
            print(f"❌ Error loading students: {e}")
        
        return target_students
    
    def create_course(self) -> bool:
        """
        Create the "Introduction to AI" course
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n🏗️  Step 1: Creating course '{self.course_name}'")
        
        course = self.canvas.create_course(
            name=self.course_name,
            course_code=self.course_code,
            is_public=True,
            is_public_to_auth_users=True,
            syllabus_body="Welcome to Introduction to AI! This course covers fundamental concepts in artificial intelligence."
        )
        
        if course:
            self.course_id = course['id']
            print(f"✅ Course created successfully!")
            print(f"   Course ID: {self.course_id}")
            print(f"   Course URL: http://{all_token_key_session.canvas_admin_domain}/courses/{self.course_id}")
            return True
        else:
            print(f"❌ Failed to create course")
            return False
    
    def add_teacher(self) -> bool:
        """
        Add current user as teacher to the course
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n👨‍🏫 Step 2: Adding teacher to course")

        teacher_user = self.canvas.find_user_by_email(teacher_email, 1)
        if teacher_user:
            teacher_enrollment = self.canvas.add_teacher_to_course(self.course_id, teacher_user['id'])
            if teacher_enrollment:
                print(f"✅ Added {teacher_user['name']} ({teacher_email}) as teacher")
                return True
        else:
            print(f"❌ Failed to add teacher")
            return False
        
        teacher_enrollment = self.canvas.add_teacher_to_course(self.course_id, teacher_email)
        if teacher_enrollment:
            print(f"✅ Added {current_user['name']} as teacher")
            return True
        else:
            print(f"❌ Failed to add teacher")
            return False
    
    def enroll_students(self, target_students: List[Tuple[str, str]]) -> bool:
        """
        Enroll target students in the course
        
        Args:
            target_students: List of (name, email) tuples
            
        Returns:
            True if all enrollments successful, False otherwise
        """
        print(f"\n👥 Step 3: Enrolling {len(target_students)} target students")
        
        stats = self.canvas.batch_enroll_students(
            course_id=self.course_id,
            students=target_students,
            account_id=1
        )
        
        success = stats['successful'] == len(target_students)
        if success:
            print(f"✅ All {len(target_students)} students enrolled successfully!")
        else:
            print(f"⚠️  {stats['successful']}/{len(target_students)} students enrolled")
        
        return success
    
    def create_assignments(self) -> bool:
        """
        Create assignments from markdown files in the assignments directory
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n📝 Step 4: Creating assignments from {self.assignments_dir}")
        
        if not self.assignments_dir.exists():
            print(f"❌ Assignments directory not found: {self.assignments_dir}")
            return False
        
        # Delete all existing assignments first
        print(f"🗑️  Step 4.1: Clearing existing assignments in course {self.course_id}")
        if not self.canvas.delete_all_assignments(self.course_id):
            print(f"⚠️  Failed to delete some existing assignments, but continuing...")
        
        # Create new assignments from markdown files
        print(f"📝 Step 4.2: Creating new assignments from markdown files")
        stats = self.canvas.batch_create_assignments_from_md(
            course_id=self.course_id,
            md_directory=str(self.assignments_dir),
            points_possible=100,
            due_days_interval=7,  # 7 days apart
            published=True
        )
        
        success = stats['successful'] > 0
        if success:
            print(f"✅ Created {stats['successful']}/{stats['total']} assignments")
            print(f"📋 Assignments created:")
            for assignment in stats['assignments']:
                print(f"   - {assignment['name']} (ID: {assignment['assignment_id']})")
        else:
            print(f"❌ Failed to create assignments")
        
        return success
    
    def publish_course(self) -> bool:
        """
        Publish the course to make it available
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n📤 Step 5: Publishing course")
        
        if self.canvas.publish_course(self.course_id):
            print(f"✅ Course published successfully!")
            return True
        else:
            print(f"❌ Failed to publish course")
            return False

    def delete_all_quizzes_in_course(self) -> bool:
        """
        Delete all quizzes in the course
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n🗑️  Step 4.1: Deleting all quizzes in course")
        return self.canvas.delete_all_quizzes_in_course(self.course_id)
    
    def delete_all_assignments_in_course(self) -> bool:
        """
        Delete all assignments in the course
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n🗑️  Step 4.1: Deleting all assignments in course")
        return self.canvas.delete_all_assignments(self.course_id)
    
    def run_pipeline(self) -> bool:
        """
        Execute the complete preprocessing pipeline
        
        Returns:
            True if all steps successful, False otherwise
        """
        print(f"🚀 Canvas Course Preprocessing Pipeline")
        print(f"=" * 60)
        print(f"Task: Set up '{self.course_name}' course with specific students and assignments")
        
        if self.agent_workspace:
            print(f"Agent workspace: {self.agent_workspace}")
        
        # Test Canvas connection
        current_user = self.canvas.get_current_user()
        if not current_user:
            print(f"❌ Failed to connect to Canvas. Check URL and token.")
            return False
        
        print(f"✅ Connected to Canvas as: {current_user['name']}")
        
        # Load target students
        target_students = self.load_target_students()
        if not target_students:
            print(f"❌ No target students loaded")
            return False
        
        # Execute pipeline steps
        steps = [
            ("Create Course", lambda: self.create_course()),
            ("Add Teacher", lambda: self.add_teacher()),
            ("Enroll Students", lambda: self.enroll_students(target_students)),
            ("Create Assignments", lambda: self.create_assignments()),
            ("Delete All Quizzes", lambda: self.delete_all_quizzes_in_course()),
            ("Publish Course", lambda: self.publish_course())
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                print(f"\n❌ Pipeline failed at step: {step_name}")
                return False
        
        # Final summary
        print(f"\n🎉 Pipeline completed successfully!")
        print(f"📊 Summary:")
        print(f"   Course: {self.course_name} (ID: {self.course_id})")
        print(f"   Students enrolled: {len(target_students)}")
        print(f"   Assignments created: 2 (homework1, project1)")
        print(f"   Course status: Published")
        print(f"   Direct link: http://{all_token_key_session.canvas_admin_domain}/courses/{self.course_id}")
        
        return True


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace directory (for compatibility)")
    parser.add_argument("--canvas_url", default=None,
                       help="Canvas base URL (defaults to config file)")
    parser.add_argument("--canvas_token", default=None, 
                       help="Canvas API access token (defaults to config file)")
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    print("🎓 Canvas Course Preprocessing - Art History")
    print("Setting up course with specific students and assignments...")
    
    # Display configuration
    canvas_url = args.canvas_url or f"http://{all_token_key_session.canvas_admin_domain}"
    canvas_token = args.canvas_token or all_token_key_session.canvas_admin_api_token
    print(f"📋 Configuration:")
    print(f"   Canvas URL: {canvas_url}")
    print(f"   Canvas Token: {canvas_token[:10]}...{canvas_token[-4:] if len(canvas_token) > 14 else canvas_token}")
    
    # Initialize and run pipeline
    pipeline = CanvasPreprocessPipeline(
        canvas_url=args.canvas_url,
        canvas_token=args.canvas_token,
        agent_workspace=args.agent_workspace
    )
    
    try:
        success = pipeline.run_pipeline()
        if success:
            print(f"\n✅ Canvas course preprocessing completed successfully!")
            print(f"Ready for Canvas notification task execution.")
        else:
            print(f"\n❌ Canvas course preprocessing failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("Canvas course setup completed! Course is ready for notification tasks.")