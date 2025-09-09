#!/usr/bin/env python3
"""
Debug script to test Canvas API token functionality
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

def test_canvas_connection():
    """Test Canvas API connection and token functionality"""
    print("Canvas API Token Debug Script")
    print("=" * 50)
    
    # Display token info
    token = all_token_key_session.canvas_api_token
    print(f"Token from config: {token[:10]}...{token[-4:] if len(token) > 14 else token}")
    
    # Test API connection
    canvas_url = "http://localhost:10001"
    print(f"Canvas URL: {canvas_url}")
    
    try:
        # Initialize Canvas API
        canvas = CanvasAPI(canvas_url, token)
        print("Canvas API initialized successfully")
        
        # Test current user
        print("\nTesting current user...")
        current_user = canvas.get_current_user()
        if current_user:
            print(f"Connected as: {current_user['name']} (ID: {current_user['id']})")
            print(f"User type: {current_user.get('roles', 'Unknown')}")
        else:
            print("Failed to get current user - token may be invalid")
            return False
        
        # Test course listing
        print("\nTesting course listing...")
        courses = canvas.list_courses()
        if courses is None:
            print("Failed to retrieve courses - API error")
            return False
        elif len(courses) == 0:
            print("No courses found - this may be the issue")
            return False
        else:
            print(f"Found {len(courses)} courses:")
            for i, course in enumerate(courses):  # Show all courses
                course_id = course.get('id', 'Unknown')
                course_name = course.get('name', 'Unknown')
                course_state = course.get('workflow_state', 'Unknown')
                print(f"  {i+1}. {course_name} (ID: {course_id}, State: {course_state})")
                
                # Check if this is our target course
                if course_name == "Introduction to AI":
                    print(f"    >>> Found target course: Introduction to AI (ID: {course_id})")
        
        return True
        
    except Exception as e:
        print(f"Error during Canvas API testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_canvas_connection()
    if success:
        print("\nCanvas API connection test PASSED")
    else:
        print("\nCanvas API connection test FAILED")
        sys.exit(1)