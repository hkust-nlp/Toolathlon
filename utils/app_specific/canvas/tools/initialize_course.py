#!/usr/bin/env python3
"""
Canvas Course Quick Initializer

This script provides a command-line interface for quickly initializing Canvas courses
with specified parameters including course name, student CSV file, and student limits.

Usage:
    python initialize_course.py --name "Course Name" --code "COURSE001" --csv students.csv --limit 10
"""

import argparse
import os
import sys
from pathlib import Path

# Import Canvas API from parent utils module
from ..api_client import CanvasAPI, CourseInitializer


def main():
    parser = argparse.ArgumentParser(
        description='Initialize a Canvas course with students from CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create course with first 5 students
    python initialize_course.py --name "Python Programming" --code "PY101" --csv student_list.csv --limit 5
    
    # Create course with all students from CSV
    python initialize_course.py --name "Data Science" --code "DS201" --csv students.csv
    
    # Create course without publishing it
    python initialize_course.py --name "Test Course" --code "TEST" --csv students.csv --no-publish
    
    # Create course with custom Canvas settings
    python initialize_course.py --name "Advanced AI" --code "AI301" --csv students.csv --url "http://localhost:10001" --token "your_token"
        """
    )
    
    # Required arguments
    parser.add_argument('--name', '-n', required=True, 
                       help='Course name (e.g., "Introduction to Python")')
    parser.add_argument('--code', '-c', required=True,
                       help='Course code (e.g., "PY101")')
    parser.add_argument('--csv', required=True,
                       help='Path to CSV file with student data (columns: Name, email)')
    
    # Optional arguments
    parser.add_argument('--limit', '-l', type=int, default=None,
                       help='Maximum number of students to enroll (default: all)')
    parser.add_argument('--url', default='http://localhost:10001',
                       help='Canvas base URL (default: http://localhost:10001)')
    parser.add_argument('--token', default='mcpcanvasadmintoken1',
                       help='Canvas access token (default: mcpcanvasadmintoken1)')
    parser.add_argument('--account-id', type=int, default=1,
                       help='Canvas account ID (default: 1)')
    parser.add_argument('--no-publish', action='store_true',
                       help='Do not publish the course after creation')
    parser.add_argument('--no-teacher', action='store_true',
                       help='Do not add current user as teacher')
    
    # Course customization options
    parser.add_argument('--syllabus', default='',
                       help='Course syllabus content')
    parser.add_argument('--start-date',
                       help='Course start date (ISO format: YYYY-MM-DDTHH:MM:SSZ)')
    parser.add_argument('--end-date',
                       help='Course end date (ISO format: YYYY-MM-DDTHH:MM:SSZ)')
    
    args = parser.parse_args()
    
    # Validate CSV file exists
    if not os.path.exists(args.csv):
        print(f"❌ Error: CSV file not found: {args.csv}")
        return 1
    
    # Initialize Canvas API
    print(f"🔗 Connecting to Canvas at {args.url}")
    canvas = CanvasAPI(args.url, args.token)
    
    # Test connection
    current_user = canvas.get_current_user()
    if not current_user:
        print("❌ Error: Failed to connect to Canvas. Check your URL and token.")
        return 1
    
    print(f"✅ Connected as: {current_user['name']} ({current_user.get('login_id', 'N/A')})")
    
    # Prepare course parameters
    course_kwargs = {}
    if args.syllabus:
        course_kwargs['syllabus_body'] = args.syllabus
    if args.start_date:
        course_kwargs['start_at'] = args.start_date
    if args.end_date:
        course_kwargs['end_at'] = args.end_date
    
    # Initialize course
    initializer = CourseInitializer(canvas)
    
    course = initializer.initialize_course(
        course_name=args.name,
        course_code=args.code,
        csv_file_path=args.csv,
        student_limit=args.limit,
        account_id=args.account_id,
        add_self_as_teacher=not args.no_teacher,
        publish=not args.no_publish,
        **course_kwargs
    )
    
    if course:
        print(f"\n🎯 Success! Course '{args.name}' (ID: {course['id']}) is ready!")
        print(f"   Direct link: {args.url}/courses/{course['id']}")
        return 0
    else:
        print("\n❌ Course initialization failed!")
        return 1


def quick_demo():
    """Demo function for quick testing with default parameters"""
    print("🚀 Running Quick Demo with Default Parameters")
    print("=" * 50)
    
    # Default configuration
    CANVAS_URL = "http://localhost:10001"
    CANVAS_TOKEN = "mcpcanvasadmintoken1"
    CSV_FILE = "initial_workspace/student_list.csv"
    
    # Initialize Canvas API
    canvas = CanvasAPI(CANVAS_URL, CANVAS_TOKEN)
    initializer = CourseInitializer(canvas)
    
    # Create a demo course
    course = initializer.initialize_course(
        course_name="Demo Course - Quick Test",
        course_code="DEMO001",
        csv_file_path=CSV_FILE,
        student_limit=3,  # Only first 3 students
        account_id=1,
        add_self_as_teacher=True,
        publish=True,
        syllabus_body="This is a demo course created by the Canvas API script."
    )
    
    if course:
        print(f"\n🎯 Demo completed! Course ID: {course['id']}")
    else:
        print("\n❌ Demo failed!")


if __name__ == "__main__":
    import sys
    
    # If no arguments provided, run demo
    if len(sys.argv) == 1:
        print("No arguments provided. Running quick demo...")
        quick_demo()
    else:
        exit_code = main()
        sys.exit(exit_code)