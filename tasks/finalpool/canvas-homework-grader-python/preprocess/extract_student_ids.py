#!/usr/bin/env python3
"""
Extract Canvas Student IDs Script

This script extracts Canvas student user IDs from a course and saves them to a CSV file.
This helps solve the issue of mapping student emails to Canvas user IDs during grading.
"""

import csv
import sys
import json
from pathlib import Path
from argparse import ArgumentParser


def load_teacher_info(csv_file_path):
    """Load teacher information from CSV file"""
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                return {
                    'name': row['Name'].strip(),
                    'email': row['email'].strip(),
                    'password': row['password'].strip(),
                    'canvas_token': row.get('canvas_token', '').strip()
                }
    except Exception as e:
        print(f"❌ Error loading teacher info: {e}")
        return None


def setup_canvas_api():
    """Setup Canvas API client"""
    try:
        # Add the utils path for import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent
        finalpool_dir = task_dir.parent
        tasks_dir = finalpool_dir.parent
        toolathlon_root = tasks_dir.parent
        utils_dir = toolathlon_root / "utils"
        
        sys.path.insert(0, str(utils_dir))
        from app_specific.canvas import CanvasAPI
        
        # Get Canvas token from token_key_session.py
        try:
            base_dir = task_dir
            sys.path.insert(0, str(base_dir))
            from token_key_session import all_token_key_session
            canvas_url = "http://localhost:10001"
            canvas_token = all_token_key_session.admin_canvas_api_token
        except ImportError:
            print("❌ Failed to import canvas token/key")
            return None, None
        
        # Create Canvas API instance
        canvas_api = CanvasAPI(canvas_url, canvas_token)
        
        # Test connection
        current_user = canvas_api.get_current_user()
        if not current_user:
            print("❌ Failed to connect to Canvas")
            return None, None
        
        print(f"✅ Connected to Canvas as: {current_user.get('name', 'Unknown')}")
        return canvas_api, canvas_url
        
    except Exception as e:
        print(f"❌ Canvas API setup failed: {e}")
        return None, None


def find_cs5123_course(canvas_api):
    """Find the CS5123 Programming Fundamentals course"""
    try:
        # Get all courses to find existing CS5123 course
        all_courses = canvas_api.list_courses(include_deleted=True, account_id=1)
        
        if all_courses:
            for course in all_courses:
                course_name = course.get('name', '')
                course_code = course.get('course_code', '')
                
                # Check if it's a CS5123 course
                if (course_code == 'CS5123'):
                    return course
                    
        print("❌ No CS5123 course found")
        return None
        
    except Exception as e:
        print(f"❌ Error finding CS5123 course: {e}")
        return None


def extract_student_ids(canvas_api, course_id):
    """Extract student user IDs from the course"""
    try:
        print(f"🔍 Extracting student IDs from course {course_id}...")
        
        # Get course enrollments
        enrollments = canvas_api.get_course_enrollments(course_id)
        
        if not enrollments:
            print("❌ No enrollments found")
            return []
        
        students = []
        for enrollment in enrollments:
            # Only process student enrollments
            if enrollment.get('type') == 'StudentEnrollment':
                user = enrollment.get('user', {})
                student_data = {
                    'canvas_user_id': user.get('id'),
                    'name': user.get('name', 'Unknown'),
                    'email': user.get('email', 'unknown@example.com'),
                    'enrollment_state': enrollment.get('enrollment_state', 'unknown')
                }
                students.append(student_data)
        
        print(f"✅ Found {len(students)} students")
        return students
        
    except Exception as e:
        print(f"❌ Error extracting student IDs: {e}")
        return []


def save_student_ids_to_csv(students, output_path):
    """Save student IDs to CSV file"""
    try:
        # Ensure the output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['canvas_user_id', 'name', 'email', 'enrollment_state']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for student in students:
                writer.writerow(student)
        
        print(f"✅ Student IDs saved to: {output_path}")
        print(f"   Total students: {len(students)}")
        
        # Display the mapping for reference
        print("\n📋 Student ID Mapping:")
        print("Canvas User ID | Name | Email")
        print("-" * 60)
        for student in students:
            print(f"{student['canvas_user_id']:13} | {student['name'][:20]:<20} | {student['email']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return False


def main():
    """Main function to extract student IDs"""
    parser = ArgumentParser(description="Extract Canvas Student IDs to CSV")
    parser.add_argument("--output",
                       help="Output CSV file path (relative to script directory)")
    parser.add_argument("--course-id", type=int,
                       help="Specific course ID to extract from (optional)")
    
    args = parser.parse_args()
    
    print("🆔 Canvas Student ID Extractor")
    print("=" * 50)
    
    # Setup paths
    script_dir = Path(__file__).parent
    
    # Convert relative output path to absolute
    if not Path(args.output).is_absolute():
        output_path = script_dir / args.output
    else:
        output_path = Path(args.output)
    
    print(f"📁 Output file: {output_path}")
    
    # Setup Canvas API
    canvas_api, canvas_url = setup_canvas_api()
    if not canvas_api:
        sys.exit(1)
    
    # Find or use specified course
    if args.course_id:
        course_id = args.course_id
        print(f"🎯 Using specified course ID: {course_id}")
    else:
        # Find CS5123 course
        course = find_cs5123_course(canvas_api)
        if not course:
            print("❌ Could not find CS5123 course")
            print("💡 Try running with --course-id <ID> to specify course manually")
            sys.exit(1)
        
        course_id = course['id']
        course_name = course.get('name', 'CS5123')
        print(f"✅ Found course: {course_name} (ID: {course_id})")
    
    # Extract student IDs
    students = extract_student_ids(canvas_api, course_id)
    if not students:
        print("❌ No students found to extract")
        sys.exit(1)
    
    # Save to CSV
    if save_student_ids_to_csv(students, output_path):
        print(f"\n🎉 Successfully extracted {len(students)} student IDs!")
        print(f"🔗 Canvas course URL: {canvas_url}/courses/{course_id}")
        print(f"📄 Student IDs saved to: {output_path}")
        print("\n💡 This CSV can now be used by the grading agent to map emails to Canvas user IDs")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()