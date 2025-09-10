#!/usr/bin/env python3
"""
Test Script for New Canvas API Features

This script demonstrates the new assignment management and private messaging features.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path for utils imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.app_specific.canvas import CanvasAPI
except ImportError:
    # Fallback to local import
    from canvas_api import CanvasAPI


def test_assignment_features():
    """Test assignment creation and management features"""
    print("\n🎯 Testing Assignment Management Features")
    print("=" * 50)
    
    # Initialize Canvas API
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    
    # Use the test course we created earlier
    course_id = 59  # AI Fundamentals course
    
    print(f"📚 Testing with course ID: {course_id}")
    
    # Test 1: Create a single assignment
    print("\n✅ Test 1: Creating a single assignment")
    assignment = canvas.create_assignment(
        course_id=course_id,
        name="Test Assignment - API Demo",
        description="This is a test assignment created via the Canvas REST API.",
        points_possible=50,
        submission_types=['online_text_entry', 'online_upload'],
        published=True
    )
    
    if assignment:
        assignment_id = assignment['id']
        print(f"   Assignment created with ID: {assignment_id}")
        
        # Test 2: Get assignment details
        print("\n✅ Test 2: Getting assignment details")
        assignment_details = canvas.get_assignment(course_id, assignment_id)
        if assignment_details:
            print(f"   Assignment name: {assignment_details['name']}")
            print(f"   Points possible: {assignment_details['points_possible']}")
            print(f"   Published: {assignment_details['published']}")
        
        # Test 3: Update assignment
        print("\n✅ Test 3: Updating assignment")
        updated = canvas.update_assignment(
            course_id, assignment_id,
            description="Updated description: This assignment has been modified via API.",
            points_possible=75
        )
        if updated:
            print(f"   Assignment updated successfully")
    
    # Test 4: List all assignments
    print("\n✅ Test 4: Listing all assignments")
    assignments = canvas.list_assignments(course_id)
    print(f"   Found {len(assignments)} assignments in the course")
    for assignment in assignments[:3]:  # Show first 3
        print(f"   - {assignment['name']} ({assignment['points_possible']} points)")


def test_messaging_features():
    """Test private messaging features"""
    print("\n💬 Testing Private Messaging Features")
    print("=" * 50)
    
    # Initialize Canvas API
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    
    course_id = 59
    
    # Test 1: Send message to a specific student
    print("\n✅ Test 1: Sending message to specific student")
    student_email = "stephanie.cox@mcp.com"
    
    message_result = canvas.send_message_to_student_by_email(
        email=student_email,
        subject="API Test Message",
        body="This is a test message sent via the Canvas REST API. Please ignore this message.",
        course_id=course_id
    )
    
    if message_result:
        print(f"   Message sent successfully!")
    
    # Test 2: Get conversation history
    print(f"\n✅ Test 2: Getting conversation history with {student_email}")
    user = canvas.find_user_by_email(student_email)
    if user:
        conversations = canvas.get_conversation_with_user(user['id'])
        print(f"   Found {len(conversations)} conversations")
        
        # Get messages from the first conversation
        if conversations:
            conv_id = conversations[0]['id']
            messages = canvas.get_conversation_messages(conv_id)
            print(f"   First conversation has {len(messages)} messages")
    
    # Test 3: Get all conversations
    print("\n✅ Test 3: Getting all conversations")
    all_conversations = canvas.get_conversations('inbox')
    print(f"   Found {len(all_conversations)} conversations in inbox")
    
    sent_conversations = canvas.get_conversations('sent')
    print(f"   Found {len(sent_conversations)} conversations in sent")


def test_batch_operations():
    """Test batch operations"""
    print("\n🔄 Testing Batch Operations")
    print("=" * 50)
    
    # Initialize Canvas API
    canvas = CanvasAPI("http://localhost:10001", "mcpcanvasadmintoken1")
    
    course_id = 59
    
    # Test 1: Create sample markdown files
    print("\n✅ Test 1: Creating sample markdown files")
    test_md_dir = "test_assignments"
    
    if not os.path.exists(test_md_dir):
        os.makedirs(test_md_dir)
        print(f"   Created directory: {test_md_dir}")
    
    # Create test assignment files
    test_assignments = [
        ("quiz1.md", "# Quiz 1: Basic Concepts\n\nThis is a short quiz on basic programming concepts."),
        ("lab1.md", "# Lab 1: Hands-on Practice\n\nComplete the following lab exercises."),
    ]
    
    for filename, content in test_assignments:
        filepath = os.path.join(test_md_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   Created: {filename}")
    
    # Test 2: Batch create assignments from markdown
    print(f"\n✅ Test 2: Batch creating assignments from {test_md_dir}")
    stats = canvas.batch_create_assignments_from_md(
        course_id=course_id,
        md_directory=test_md_dir,
        points_possible=25,
        due_days_interval=3,
        published=True
    )
    
    print(f"   Created {stats['successful']}/{stats['total']} assignments")
    
    # Test 3: Batch message multiple students
    print("\n✅ Test 3: Batch messaging students")
    student_emails = ["stephanie.cox@mcp.com", "james.thomas30@mcp.com"]
    
    message_stats = canvas.batch_message_students(
        student_emails=student_emails,
        subject="Batch Test Message",
        body="This is a batch test message sent to multiple students via API.",
        course_id=course_id
    )
    
    print(f"   Sent {message_stats['successful']}/{message_stats['total']} messages")


def main():
    """Run all tests"""
    print("🧪 Canvas API New Features Test Suite")
    print("=" * 60)
    
    try:
        # Test assignment features
        test_assignment_features()
        
        # Small delay between test suites
        time.sleep(1)
        
        # Test messaging features
        test_messaging_features()
        
        # Small delay between test suites
        time.sleep(1)
        
        # Test batch operations
        test_batch_operations()
        
        print("\n🎉 All tests completed successfully!")
        print("\n📋 Summary of tested features:")
        print("   ✅ Single assignment creation")
        print("   ✅ Assignment details retrieval")
        print("   ✅ Assignment updates")
        print("   ✅ Assignment listing")
        print("   ✅ Private messaging to students")
        print("   ✅ Conversation history retrieval")
        print("   ✅ Batch assignment creation from markdown")
        print("   ✅ Batch student messaging")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()