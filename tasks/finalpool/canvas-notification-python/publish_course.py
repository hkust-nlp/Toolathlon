#!/usr/bin/env python3
"""
Canvas Course Publisher Script

This script uses the Canvas REST API to publish courses that cannot be published 
through the MCP interface.
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

class CanvasAPI:
    def __init__(self, base_url: str, access_token: str):
        """
        Initialize Canvas API client
        
        Args:
            base_url: Canvas instance base URL (e.g., 'http://localhost:10001')
            access_token: Canvas API access token
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_course(self, course_id: int) -> Optional[Dict[Any, Any]]:
        """
        Get course information
        
        Args:
            course_id: Course ID
            
        Returns:
            Course data or None if not found
        """
        url = f"{self.base_url}/api/v1/courses/{course_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting course {course_id}: {e}")
            return None
    
    def publish_course(self, course_id: int) -> bool:
        """
        Publish a course using Canvas REST API
        
        Canvas API endpoint: PUT /api/v1/courses/:id
        The key is to set the 'event' parameter to 'offer'
        
        Args:
            course_id: Course ID to publish
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/api/v1/courses/{course_id}"
        
        # The magic parameter to publish a course
        data = {
            'course': {
                'event': 'offer'
            }
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            course_data = response.json()
            workflow_state = course_data.get('workflow_state', 'unknown')
            
            if workflow_state == 'available':
                print(f"✅ Course {course_id} successfully published!")
                print(f"   Workflow state: {workflow_state}")
                return True
            else:
                print(f"❌ Course {course_id} publish failed.")
                print(f"   Workflow state: {workflow_state}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error publishing course {course_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Response text: {e.response.text}")
            return False
    
    def unpublish_course(self, course_id: int) -> bool:
        """
        Unpublish a course using Canvas REST API
        
        Args:
            course_id: Course ID to unpublish
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/api/v1/courses/{course_id}"
        
        data = {
            'course': {
                'event': 'claim'
            }
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            course_data = response.json()
            workflow_state = course_data.get('workflow_state', 'unknown')
            
            if workflow_state == 'unpublished':
                print(f"✅ Course {course_id} successfully unpublished!")
                print(f"   Workflow state: {workflow_state}")
                return True
            else:
                print(f"❌ Course {course_id} unpublish failed.")
                print(f"   Workflow state: {workflow_state}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error unpublishing course {course_id}: {e}")
            return False


def main():
    """Main function to publish courses"""
    
    # Canvas configuration
    CANVAS_BASE_URL = "http://localhost:10001"
    CANVAS_ACCESS_TOKEN = "mcpcanvasadmintoken1"  # From the .mcp.json file
    
    # Course IDs to publish
    COURSE_IDS = [41, 45]  # test1 and test2 courses
    
    # Initialize Canvas API client
    canvas = CanvasAPI(CANVAS_BASE_URL, CANVAS_ACCESS_TOKEN)
    
    print("🚀 Canvas Course Publisher")
    print("=" * 50)
    
    for course_id in COURSE_IDS:
        print(f"\n📚 Processing course ID: {course_id}")
        
        # Get current course status
        course_info = canvas.get_course(course_id)
        if not course_info:
            print(f"❌ Could not retrieve course {course_id}")
            continue
        
        course_name = course_info.get('name', 'Unknown')
        current_state = course_info.get('workflow_state', 'unknown')
        
        print(f"   Course: {course_name}")
        print(f"   Current state: {current_state}")
        
        if current_state == 'unpublished':
            print(f"   📤 Publishing course...")
            success = canvas.publish_course(course_id)
            if not success:
                print(f"   ❌ Failed to publish course {course_id}")
        elif current_state == 'available':
            print(f"   ✅ Course is already published!")
        else:
            print(f"   ⚠️  Course is in unexpected state: {current_state}")
    
    print("\n🎉 Publishing process completed!")


if __name__ == "__main__":
    main()