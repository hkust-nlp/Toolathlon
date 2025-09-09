#!/usr/bin/env python3
"""
Canvas API Usage Examples

This file demonstrates various ways to use the Canvas API library
for different course management scenarios.
"""

import sys
from pathlib import Path

# Add project root to path for utils imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.app_specific.canvas import CanvasAPI, CourseInitializer
except ImportError:
    # Fallback to local import
    from canvas_api import CanvasAPI, CourseInitializer


def example_1_basic_course_creation():
    """Example 1: Basic course creation with manual steps"""
    print("\n" + "="*60)
    print("Example 1: Basic Course Creation")
    print("="*60)
    
    # Initialize Canvas API
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    
    # Create course
    course = canvas.create_course("Advanced Python", "PY301")
    if not course:
        return
    
    course_id = course['id']
    
    # Add current user as teacher
    current_user = canvas.get_current_user()
    if current_user:
        canvas.add_teacher_to_course(course_id, current_user['id'])
    
    # Load students and enroll them
    students = canvas.load_students_from_csv("initial_workspace/student_list.csv", limit=3)
    canvas.batch_enroll_students(course_id, students)
    
    # Publish course
    canvas.publish_course(course_id)
    
    print(f"✅ Course created and configured: {course_id}")


def example_2_quick_initialization():
    """Example 2: Quick course initialization using CourseInitializer"""
    print("\n" + "="*60)
    print("Example 2: Quick Course Initialization")
    print("="*60)
    
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    initializer = CourseInitializer(canvas)
    
    course = initializer.initialize_course(
        course_name="Machine Learning Basics",
        course_code="ML101",
        csv_file_path="initial_workspace/student_list.csv",
        student_limit=5,
        syllabus_body="Introduction to machine learning concepts and applications.",
        start_at="2025-09-01T00:00:00Z",
        end_at="2025-12-31T23:59:59Z"
    )
    
    if course:
        print(f"✅ Quick initialization completed: {course['id']}")


def example_3_batch_course_creation():
    """Example 3: Create multiple courses with different configurations"""
    print("\n" + "="*60)
    print("Example 3: Batch Course Creation")
    print("="*60)
    
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    initializer = CourseInitializer(canvas)
    
    # Course configurations
    courses_config = [
        {
            "name": "Web Development Fundamentals",
            "code": "WEB101",
            "student_limit": 4,
            "syllabus": "Learn HTML, CSS, and JavaScript basics"
        },
        {
            "name": "Database Design",
            "code": "DB201", 
            "student_limit": 3,
            "syllabus": "Relational database design and SQL"
        },
        {
            "name": "Software Engineering",
            "code": "SE301",
            "student_limit": 6,
            "syllabus": "Software development lifecycle and best practices"
        }
    ]
    
    created_courses = []
    
    for config in courses_config:
        print(f"\n🚀 Creating: {config['name']}")
        course = initializer.initialize_course(
            course_name=config['name'],
            course_code=config['code'],
            csv_file_path="initial_workspace/student_list.csv",
            student_limit=config['student_limit'],
            syllabus_body=config['syllabus']
        )
        
        if course:
            created_courses.append(course)
    
    print(f"\n✅ Batch creation completed! Created {len(created_courses)} courses:")
    for course in created_courses:
        print(f"   - {course['name']} (ID: {course['id']})")


def example_4_course_management():
    """Example 4: Course management operations"""
    print("\n" + "="*60)
    print("Example 4: Course Management Operations")
    print("="*60)
    
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    
    # Create a test course
    course = canvas.create_course("Test Management Course", "TEST999")
    if not course:
        return
    
    course_id = course['id']
    
    print(f"📚 Created course: {course_id}")
    
    # Get course info
    course_info = canvas.get_course(course_id)
    print(f"📊 Course status: {course_info['workflow_state']}")
    
    # Publish course
    canvas.publish_course(course_id)
    
    # Check status again
    course_info = canvas.get_course(course_id)
    print(f"📊 Course status after publish: {course_info['workflow_state']}")
    
    # Unpublish course
    canvas.unpublish_course(course_id)
    
    # Final status check
    course_info = canvas.get_course(course_id)
    print(f"📊 Final course status: {course_info['workflow_state']}")


def example_5_user_management():
    """Example 5: User creation and management"""
    print("\n" + "="*60)
    print("Example 5: User Management")
    print("="*60)
    
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    
    # Test user data
    test_users = [
        ("Alice Johnson", "alice.test@example.com"),
        ("Bob Smith", "bob.test@example.com"),
        ("Carol Wilson", "carol.test@example.com")
    ]
    
    print("👥 Testing user creation and lookup...")
    
    for name, email in test_users:
        print(f"\n🔍 Processing: {name} ({email})")
        
        # Try to find existing user
        existing_user = canvas.find_user_by_email(email)
        if existing_user:
            print(f"   Found existing user: {existing_user['id']}")
        else:
            print("   User not found, creating new user...")
            new_user = canvas.create_user(name, email)
            if new_user:
                print(f"   Created user: {new_user['id']}")
        
        # Test get_or_create_user function
        user = canvas.get_or_create_user(name, email)
        if user:
            print(f"   ✅ Final user ID: {user['id']}")


def main():
    """Run all examples"""
    print("🎓 Canvas API Examples")
    print("=" * 60)
    print("This script demonstrates various Canvas API usage patterns.")
    print("Choose an example to run:")
    print()
    print("1. Basic course creation with manual steps")
    print("2. Quick course initialization")
    print("3. Batch course creation")
    print("4. Course management operations")
    print("5. User management")
    print("0. Run all examples")
    print()
    
    try:
        choice = input("Enter your choice (0-5): ").strip()
        
        if choice == "1":
            example_1_basic_course_creation()
        elif choice == "2":
            example_2_quick_initialization()
        elif choice == "3":
            example_3_batch_course_creation()
        elif choice == "4":
            example_4_course_management()
        elif choice == "5":
            example_5_user_management()
        elif choice == "0":
            example_1_basic_course_creation()
            example_2_quick_initialization()
            example_3_batch_course_creation()
            example_4_course_management()
            example_5_user_management()
        else:
            print("Invalid choice!")
            return
        
        print("\n🎉 Examples completed!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Examples interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")


if __name__ == "__main__":
    main()