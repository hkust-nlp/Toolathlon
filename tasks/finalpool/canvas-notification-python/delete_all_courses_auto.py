#!/usr/bin/env python3
"""
Auto script to delete all courses belonging to this Canvas account
WARNING: This will automatically delete ALL courses without confirmation!
"""

import sys
from pathlib import Path

# Add project root to path for utils imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.app_specific.canvas import CanvasAPI
except ImportError:
    # Fallback to local import
    from canvas_api import CanvasAPI
from token_key_session import all_token_key_session

def delete_all_courses():
    """Delete all courses in the Canvas account"""
    print("🗑️  AUTO-DELETING ALL COURSES IN CANVAS ACCOUNT")
    print("=" * 60)
    
    # Initialize Canvas API
    canvas_url = "http://localhost:10001"
    canvas_token = all_token_key_session.canvas_api_token
    
    print(f"📋 Configuration:")
    print(f"   Canvas URL: {canvas_url}")
    print(f"   Canvas Token: {canvas_token[:10]}...{canvas_token[-4:]}")
    
    canvas = CanvasAPI(canvas_url, canvas_token)
    
    # Get all courses
    print("\n🔍 Fetching all courses...")
    courses = canvas.list_courses()
    
    if not courses:
        print("✅ No courses found to delete.")
        return
    
    print(f"📚 Found {len(courses)} courses:")
    for course in courses:
        print(f"   - {course['name']} (ID: {course['id']}) - {course.get('workflow_state', 'unknown')}")
    
    # Delete each course
    print(f"\n🗑️  Auto-deleting {len(courses)} courses...")
    deleted_count = 0
    failed_count = 0
    
    for i, course in enumerate(courses, 1):
        course_id = course['id']
        course_name = course['name']
        
        print(f"[{i}/{len(courses)}] Deleting: {course_name} (ID: {course_id})...", end="")
        
        if canvas.delete_course(course_id):
            print(" ✅")
            deleted_count += 1
        else:
            print(" ❌")
            failed_count += 1
    
    # Summary
    print(f"\n📊 Deletion Summary:")
    print(f"   ✅ Successfully deleted: {deleted_count}")
    print(f"   ❌ Failed to delete: {failed_count}")
    print(f"   📚 Total courses: {len(courses)}")
    
    if deleted_count > 0:
        print(f"\n🎉 Successfully deleted {deleted_count} courses!")
    
    if failed_count > 0:
        print(f"⚠️  {failed_count} courses could not be deleted (may require special permissions)")
    
    print(f"\n✅ Course deletion process completed!")

if __name__ == "__main__":
    delete_all_courses()