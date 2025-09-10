#!/usr/bin/env python3
"""
Canvas Notification Task Preprocessing

This module sets up Canvas environment for the notification task using
the centralized utils.app_specific.canvas utility functions.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path to import utils modules
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.app_specific.canvas import CanvasAPI, CanvasPreprocessUtils, create_canvas_utils
except ImportError as e:
    print(f"Error: Cannot import Canvas utils modules: {e}")
    print("Make sure utils.app_specific.canvas is properly installed.")
    sys.exit(1)


def main():
    """Main preprocessing function"""
    parser = argparse.ArgumentParser(description="Canvas Notification Task Preprocessing")
    parser.add_argument("--canvas_url", default=None, 
                       help="Canvas base URL (defaults to http://localhost:10001)")
    parser.add_argument("--canvas_token", default=None, 
                       help="Canvas API access token (defaults to admin token)")
    parser.add_argument("--agent_workspace", default=None,
                       help="Agent workspace directory (for compatibility)")
    parser.add_argument("--cleanup", action="store_true", default=True,
                       help="Clean up existing courses before setup (default: True)")
    parser.add_argument("--launch_time", required=False)
    
    args = parser.parse_args()
    
    print("Canvas Course Preprocessing - Introduction to AI")
    print("Setting up course with specific students and assignments...")
    print(f"Configuration:")
    
    # Get task directory
    task_dir = Path(__file__).parent.parent
    
    # Initialize Canvas preprocessing utilities
    try:
        # Create Canvas utils with automatic config loading
        canvas_utils = create_canvas_utils(
            task_dir=str(task_dir),
            canvas_url=args.canvas_url,
            canvas_token=args.canvas_token
        )
        
        # Display configuration
        canvas_token = canvas_utils.canvas.access_token
        print(f"   Canvas URL: {canvas_utils.canvas.base_url}")
        print(f"   Canvas Token: {canvas_token[:10]}...{canvas_token[-4:] if len(canvas_token) > 14 else canvas_token}")
        
        # Test Canvas connection
        current_user = canvas_utils.canvas.get_current_user()
        if not current_user:
            print("Failed to connect to Canvas. Check URL and token.")
            sys.exit(1)
        
        print("Canvas Course Preprocessing Pipeline")
        print("=" * 60)
        print(f"Task: Set up 'Introduction to AI' course")
        if args.agent_workspace:
            print(f"Agent workspace: {args.agent_workspace}")
        
        print(f"Connected to Canvas as: {current_user.get('name', 'Unknown')}")
        
        # Step 1: Optional cleanup
        if args.cleanup:
            print("\nCleaning up Canvas environment...")
            
            # Delete existing "Introduction to AI" courses only
            print("Deleting existing 'Introduction to AI' courses...")
            deleted_courses = canvas_utils.cleanup_courses_by_pattern("Introduction to AI")
            
            # Delete conversations related to the task
            print("Deleting all conversations...")
            deleted_conversations = canvas_utils.cleanup_conversations()
            
            print(f"Cleanup complete: {deleted_courses} 'Introduction to AI' courses, {deleted_conversations} conversations deleted")
            print("Canvas environment is ready for fresh 'Introduction to AI' course setup")
        
        # Step 2: Create course
        print("\nStep: Create Course")
        course = canvas_utils.create_course_with_config(
            course_name="Introduction to AI",
            course_code="AI101",
            account_id=1,
            is_public=True,
            is_public_to_auth_users=True,
            syllabus_body="Welcome to Introduction to AI!"
        )
        
        if not course:
            print("Failed to create course")
            sys.exit(1)
            
        course_id = course['id']
        
        # Step 3: Enroll students from CSV
        print("\nStep: Enroll Students")
        student_csv = task_dir / "student_list.csv"
        if not student_csv.exists():
            student_csv = task_dir / "preprocess" / "student_list.csv"
        
        if student_csv.exists():
            # Enroll specific students by index (positions 1, 3, 5, 10, 15 -> 0-based: 0, 2, 4, 9, 14)
            selected_indices = [0, 2, 4, 9, 14]
            
            print("Loading student information from CSV...")
            stats = canvas_utils.batch_enroll_users_from_csv(
                course_id=course_id,
                csv_file=student_csv,
                role='StudentEnrollment',
                selected_indices=selected_indices
            )
            
            print(f"Student enrollment complete: {stats['successful']}/{stats['total']} students enrolled")
        else:
            print(f"Student CSV not found: {student_csv}")
            print("Skipping student enrollment")
        
        # Step 4: Add teacher (optional, non-critical)
        print("\nStep: Add Teacher")
        teacher_csv = task_dir / "teacher_list.csv"
        if not teacher_csv.exists():
            teacher_csv = task_dir / "preprocess" / "teacher_list.csv"
        
        if teacher_csv.exists():
            # Load first teacher from CSV
            try:
                import csv
                with open(teacher_csv, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    teachers_list = list(reader)
                    
                    if teachers_list:
                        teacher = teachers_list[0]
                        teacher_name = teacher.get('Name', '').strip()
                        teacher_email = teacher.get('email', '').strip()
                        
                        if teacher_name and teacher_email:
                            print(f"Adding teacher to course: {teacher_name} ({teacher_email})")
                            success = canvas_utils.add_user_to_course_by_email(
                                course_id=course_id,
                                user_email=teacher_email,
                                role='TeacherEnrollment'
                            )
                            if not success:
                                print("Teacher enrollment failed - continuing anyway (non-critical)")
                        else:
                            print("Invalid teacher data - skipping")
                    else:
                        print("No teachers found in CSV - skipping")
                        
            except Exception as e:
                print(f"Error loading teacher: {e} - skipping")
        else:
            print(f"Teacher CSV not found: {teacher_csv}")
            print("Skipping teacher setup")
        
        # Step 5: Create assignments (optional)
        print("\nStep: Create Assignments")
        assignments_dir = task_dir / "assignments"
        if not assignments_dir.exists():
            assignments_dir = task_dir / "preprocess" / "assignments"
        
        if assignments_dir.exists() and assignments_dir.is_dir():
            print("Creating assignments from directory...")
            # Use Canvas API's batch assignment creation
            stats = canvas_utils.canvas.batch_create_assignments_from_md(
                course_id=course_id,
                md_directory=str(assignments_dir),
                points_possible=100,
                due_days_interval=7,
                published=True
            )
            print(f"Created {stats['successful']}/{stats['total']} assignments")
            if stats['assignments']:
                print("📋 Assignments created:")
                for assignment in stats['assignments']:
                    print(f"   - {assignment['name']} (ID: {assignment['assignment_id']})")
        else:
            print(f"Assignments directory not found: {assignments_dir}")
            print("Skipping assignment creation")
        
        # Step 6: Publish course
        print("\nStep: Publish Course")
        if canvas_utils.canvas.publish_course(course_id):
            print("Course published successfully!")
        else:
            print("Failed to publish course - continuing anyway")
        
        # Final summary
        print("\nPipeline completed successfully!")
        print("Summary:")
        print(f"Course: Introduction to AI (ID: {course_id})")
        print(f"Course status: Published")
        print(f"Direct link: {canvas_utils.canvas.base_url}/courses/{course_id}")
        
        print("Canvas course setup completed! Course is ready for notification tasks.")
            
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()