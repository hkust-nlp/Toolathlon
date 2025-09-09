#!/usr/bin/env python3
"""
Canvas Course Manager

This script provides comprehensive course management functionality including:
- Creating courses
- Listing courses
- Deleting/concluding courses
- Publishing/unpublishing courses
- Course information retrieval

Usage:
    python course_manager.py --list-courses
    python course_manager.py --delete-course 123
    python course_manager.py --conclude-course 123
    python course_manager.py --get-course 123
"""

import argparse
import sys
from pathlib import Path

# Import Canvas API from parent utils module
from ..api_client import CanvasAPI


def confirm_deletion(course_name: str, course_id: int) -> bool:
    """Ask user to confirm course deletion"""
    print(f"\n⚠️  WARNING: You are about to delete the course:")
    print(f"   Name: {course_name}")
    print(f"   ID: {course_id}")
    print(f"\n❗ This action cannot be undone!")
    
    while True:
        response = input("\nDo you want to continue? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def main():
    parser = argparse.ArgumentParser(
        description='Canvas Course Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List all courses
    python course_manager.py --list-courses
    
    # List courses including deleted ones
    python course_manager.py --list-courses --include-deleted
    
    # Get specific course information
    python course_manager.py --get-course 59
    
    # Delete a course (permanent)
    python course_manager.py --delete-course 60
    
    # Conclude a course (soft delete)
    python course_manager.py --conclude-course 60
    
    # Force delete without confirmation
    python course_manager.py --delete-course 60 --force
    
    # Create a new course
    python course_manager.py --create-course --name "New Course" --code "NEW101"
        """
    )
    
    # Canvas connection
    parser.add_argument('--url', default='http://localhost:10001',
                       help='Canvas base URL (default: http://localhost:10001)')
    parser.add_argument('--token', default='mcpcanvasadmintoken1',
                       help='Canvas access token (default: mcpcanvasadmintoken1)')
    
    # Course operations
    course_group = parser.add_argument_group('Course Operations')
    course_group.add_argument('--list-courses', action='store_true',
                             help='List all courses')
    course_group.add_argument('--include-deleted', action='store_true',
                             help='Include deleted courses in listing')
    course_group.add_argument('--get-course', type=int, metavar='COURSE_ID',
                             help='Get information about a specific course')
    course_group.add_argument('--delete-course', type=int, metavar='COURSE_ID',
                             help='Delete a course permanently')
    course_group.add_argument('--conclude-course', type=int, metavar='COURSE_ID',
                             help='Conclude a course (soft delete)')
    course_group.add_argument('--create-course', action='store_true',
                             help='Create a new course')
    course_group.add_argument('--force', action='store_true',
                             help='Skip confirmation prompts')
    
    # Course creation parameters
    creation_group = parser.add_argument_group('Course Creation')
    creation_group.add_argument('--name',
                               help='Course name (required for creation)')
    creation_group.add_argument('--code',
                               help='Course code (required for creation)')
    creation_group.add_argument('--account-id', type=int, default=1,
                               help='Account ID for course creation (default: 1)')
    creation_group.add_argument('--publish', action='store_true',
                               help='Publish the course after creation')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.list_courses, args.get_course, args.delete_course, 
                args.conclude_course, args.create_course]):
        parser.print_help()
        return 1
    
    if args.create_course and (not args.name or not args.code):
        print("❌ Error: --name and --code are required for course creation")
        return 1
    
    # Initialize Canvas API
    print(f"🔗 Connecting to Canvas at {args.url}")
    canvas = CanvasAPI(args.url, args.token)
    
    # Test connection
    current_user = canvas.get_current_user()
    if not current_user:
        print("❌ Error: Failed to connect to Canvas. Check your URL and token.")
        return 1
    
    print(f"✅ Connected as: {current_user['name']}")
    
    # Execute operations
    if args.list_courses:
        print(f"\n📚 Listing courses...")
        courses = canvas.list_courses(include_deleted=args.include_deleted)
        
        if courses:
            print(f"Found {len(courses)} courses:")
            print(f"{'ID':<6} {'Name':<30} {'Code':<12} {'State':<15} {'Students'}")
            print("-" * 80)
            
            for course in courses:
                course_id = course.get('id', 'N/A')
                name = course.get('name', 'Unknown')[:28]
                code = course.get('course_code', 'N/A')[:10]
                state = course.get('workflow_state', 'Unknown')
                total_students = course.get('total_students', 'N/A')
                
                print(f"{course_id:<6} {name:<30} {code:<12} {state:<15} {total_students}")
        else:
            print("No courses found.")
    
    if args.get_course:
        print(f"\n📖 Getting course information for ID: {args.get_course}")
        course = canvas.get_course(args.get_course)
        
        if course:
            print(f"Course Details:")
            print(f"  ID: {course.get('id')}")
            print(f"  Name: {course.get('name')}")
            print(f"  Code: {course.get('course_code')}")
            print(f"  State: {course.get('workflow_state')}")
            print(f"  Total Students: {course.get('total_students', 'N/A')}")
            print(f"  Start Date: {course.get('start_at', 'Not set')}")
            print(f"  End Date: {course.get('end_at', 'Not set')}")
            print(f"  Published: {'Yes' if course.get('workflow_state') == 'available' else 'No'}")
            print(f"  Public: {'Yes' if course.get('is_public') else 'No'}")
        else:
            print(f"❌ Course {args.get_course} not found")
            return 1
    
    if args.delete_course:
        print(f"\n🗑️  Deleting course ID: {args.delete_course}")
        
        # Get course info first
        course = canvas.get_course(args.delete_course)
        if not course:
            print(f"❌ Course {args.delete_course} not found")
            return 1
        
        course_name = course.get('name', 'Unknown')
        
        # Confirm deletion unless --force is used
        if not args.force:
            if not confirm_deletion(course_name, args.delete_course):
                print("❌ Deletion cancelled by user")
                return 0
        
        success = canvas.delete_course(args.delete_course)
        if success:
            print(f"✅ Course deleted successfully!")
        else:
            print(f"❌ Failed to delete course")
            return 1
    
    if args.conclude_course:
        print(f"\n📁 Concluding course ID: {args.conclude_course}")
        
        # Get course info first
        course = canvas.get_course(args.conclude_course)
        if not course:
            print(f"❌ Course {args.conclude_course} not found")
            return 1
        
        course_name = course.get('name', 'Unknown')
        
        # Confirm conclusion unless --force is used
        if not args.force:
            print(f"\n⚠️  You are about to conclude the course:")
            print(f"   Name: {course_name}")
            print(f"   ID: {args.conclude_course}")
            print(f"\n💡 Concluding a course marks it as completed but keeps the data.")
            
            response = input("\nDo you want to continue? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("❌ Conclusion cancelled by user")
                return 0
        
        success = canvas.conclude_course(args.conclude_course)
        if success:
            print(f"✅ Course concluded successfully!")
        else:
            print(f"❌ Failed to conclude course")
            return 1
    
    if args.create_course:
        print(f"\n🆕 Creating new course...")
        print(f"   Name: {args.name}")
        print(f"   Code: {args.code}")
        
        course = canvas.create_course(
            name=args.name,
            course_code=args.code,
            account_id=args.account_id
        )
        
        if course:
            course_id = course['id']
            print(f"✅ Course created successfully!")
            print(f"   Course ID: {course_id}")
            
            # Add current user as teacher
            current_user = canvas.get_current_user()
            if current_user:
                canvas.add_teacher_to_course(course_id, current_user['id'])
            
            # Publish if requested
            if args.publish:
                if canvas.publish_course(course_id):
                    print(f"✅ Course published!")
                else:
                    print(f"⚠️  Course created but failed to publish")
            
            print(f"🔗 Course URL: {args.url}/courses/{course_id}")
        else:
            print(f"❌ Failed to create course")
            return 1
    
    print(f"\n🎉 Operations completed!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)