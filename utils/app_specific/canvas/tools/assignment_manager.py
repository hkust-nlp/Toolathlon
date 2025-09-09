#!/usr/bin/env python3
"""
Canvas Assignment Manager

This script provides utilities for managing Canvas assignments, including:
- Creating assignments from markdown files
- Batch assignment creation
- Assignment publishing
- Private messaging to students

Usage:
    python assignment_manager.py --course-id 59 --md-dir assignments/ --create-assignments
    python assignment_manager.py --course-id 59 --message-students --subject "Welcome" --body "Welcome to the course!"
"""

import argparse
import os
import sys
from pathlib import Path

# Import Canvas API from parent utils module
from ..api_client import CanvasAPI


def create_sample_assignments(output_dir: str):
    """Create sample assignment markdown files for testing"""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created directory: {output_dir}")
    
    sample_assignments = [
        {
            "filename": "homework1.md",
            "content": """# Homework 1: Introduction to Programming

## Objective
Learn the basics of Python programming and complete the following exercises.

## Instructions
1. Write a Python program that prints "Hello, World!"
2. Create a function that calculates the area of a rectangle
3. Write a program that asks for user input and greets the user

## Submission Requirements
- Submit your Python file (.py)
- Include comments explaining your code
- Test your program before submission

## Due Date
This assignment is due in 7 days from assignment creation.

## Grading Criteria
- Code functionality: 60%
- Code style and comments: 20%
- Testing and documentation: 20%
"""
        },
        {
            "filename": "homework2.md", 
            "content": """# Homework 2: Data Structures and Algorithms

## Objective
Implement basic data structures and algorithms in Python.

## Tasks
1. Implement a simple linked list class
2. Write a function to sort a list using bubble sort
3. Create a function that searches for an element in a list

## Requirements
- Use proper object-oriented programming principles
- Include unit tests for your implementations
- Document your code with docstrings

## Submission Format
Submit a ZIP file containing:
- Your Python source files
- Test files
- README with usage instructions

## Due Date
This assignment is due in 14 days from assignment creation.
"""
        },
        {
            "filename": "project1.md",
            "content": """# Project 1: Web Application Development

## Overview
Create a simple web application using Flask or Django framework.

## Requirements
1. User registration and login system
2. CRUD operations for a chosen data model
3. Responsive web design
4. Database integration (SQLite or PostgreSQL)

## Technical Specifications
- Use Python web framework (Flask/Django)
- Include HTML templates with CSS styling
- Implement proper error handling
- Use version control (Git)

## Deliverables
1. Source code repository (GitHub link)
2. Installation and setup instructions
3. Demo video (5-10 minutes)
4. Project documentation

## Evaluation Criteria
- Functionality: 40%
- Code quality: 30%
- Design and UX: 20%
- Documentation: 10%

## Due Date
This assignment is due in 21 days from assignment creation.
"""
        }
    ]
    
    for assignment in sample_assignments:
        file_path = os.path.join(output_dir, assignment["filename"])
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(assignment["content"])
        print(f"✅ Created sample assignment: {assignment['filename']}")
    
    print(f"\n📚 Created {len(sample_assignments)} sample assignments in {output_dir}")
    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description='Canvas Assignment and Messaging Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create assignments from markdown files
    python assignment_manager.py --course-id 59 --md-dir assignments/ --create-assignments
    
    # Create sample assignments first, then create them in Canvas
    python assignment_manager.py --course-id 59 --create-samples --create-assignments
    
    # Send welcome message to all students
    python assignment_manager.py --course-id 59 --message-students --subject "Welcome!" --body "Welcome to our course!"
    
    # Send message to specific students
    python assignment_manager.py --course-id 59 --message-students --emails "student1@mcp.com,student2@mcp.com" --subject "Assignment Reminder" --body "Please complete your assignment."
    
    # List existing assignments
    python assignment_manager.py --course-id 59 --list-assignments
    
    # Get conversation history with a student
    python assignment_manager.py --course-id 59 --get-conversations --email "student@mcp.com"
        """
    )
    
    # Required arguments
    parser.add_argument('--course-id', '-c', type=int, required=True,
                       help='Canvas course ID')
    
    # Canvas connection
    parser.add_argument('--url', default='http://localhost:10001',
                       help='Canvas base URL (default: http://localhost:10001)')
    parser.add_argument('--token', default='mcpcanvasadmintoken1',
                       help='Canvas access token (default: mcpcanvasadmintoken1)')
    
    # Assignment operations
    assignment_group = parser.add_argument_group('Assignment Operations')
    assignment_group.add_argument('--create-assignments', action='store_true',
                                 help='Create assignments from markdown files')
    assignment_group.add_argument('--md-dir', default='assignments',
                                 help='Directory containing markdown files (default: assignments)')
    assignment_group.add_argument('--points', type=float, default=100,
                                 help='Points for each assignment (default: 100)')
    assignment_group.add_argument('--due-interval', type=int, default=7,
                                 help='Days between assignment due dates (default: 7)')
    assignment_group.add_argument('--publish', action='store_true', default=True,
                                 help='Publish assignments immediately (default: True)')
    assignment_group.add_argument('--list-assignments', action='store_true',
                                 help='List existing assignments in the course')
    assignment_group.add_argument('--create-samples', action='store_true',
                                 help='Create sample assignment markdown files')
    
    # Messaging operations
    messaging_group = parser.add_argument_group('Messaging Operations')
    messaging_group.add_argument('--message-students', action='store_true',
                                help='Send messages to students')
    messaging_group.add_argument('--subject', default='Course Notification',
                                help='Message subject (default: Course Notification)')
    messaging_group.add_argument('--body', default='This is a course notification.',
                                help='Message body (default: This is a course notification.)')
    messaging_group.add_argument('--emails',
                                help='Comma-separated list of student emails (default: all course students)')
    messaging_group.add_argument('--get-conversations', action='store_true',
                                help='Get conversation history with a student')
    messaging_group.add_argument('--email',
                                help='Student email for conversation lookup')
    
    args = parser.parse_args()
    
    # Initialize Canvas API
    print(f"🔗 Connecting to Canvas at {args.url}")
    canvas = CanvasAPI(args.url, args.token)
    
    # Test connection
    current_user = canvas.get_current_user()
    if not current_user:
        print("❌ Error: Failed to connect to Canvas. Check your URL and token.")
        return 1
    
    print(f"✅ Connected as: {current_user['name']}")
    
    # Verify course exists
    course = canvas.get_course(args.course_id)
    if not course:
        print(f"❌ Error: Course {args.course_id} not found.")
        return 1
    
    print(f"📚 Working with course: {course['name']} (ID: {args.course_id})")
    
    # Create sample assignments if requested
    if args.create_samples:
        print(f"\n📝 Creating sample assignments...")
        args.md_dir = create_sample_assignments(args.md_dir)
    
    # Assignment operations
    if args.create_assignments:
        print(f"\n📚 Creating assignments from {args.md_dir}...")
        
        if not os.path.exists(args.md_dir):
            print(f"❌ Error: Markdown directory not found: {args.md_dir}")
            return 1
        
        stats = canvas.batch_create_assignments_from_md(
            course_id=args.course_id,
            md_directory=args.md_dir,
            points_possible=args.points,
            due_days_interval=args.due_interval,
            published=args.publish
        )
        
        print(f"\n🎯 Assignment creation completed!")
        print(f"   Created: {stats['successful']}/{stats['total']} assignments")
        
        if stats['assignments']:
            print(f"\n📋 Created assignments:")
            for assignment in stats['assignments']:
                print(f"   - {assignment['name']} (ID: {assignment['assignment_id']})")
    
    if args.list_assignments:
        print(f"\n📋 Listing assignments in course {args.course_id}...")
        assignments = canvas.list_assignments(args.course_id)
        
        if assignments:
            print(f"Found {len(assignments)} assignments:")
            for assignment in assignments:
                status = "Published" if assignment.get('published') else "Unpublished"
                due_date = assignment.get('due_at', 'No due date')
                points = assignment.get('points_possible', 'No points')
                print(f"   - {assignment['name']} (ID: {assignment['id']}) - {status}")
                print(f"     Points: {points}, Due: {due_date}")
        else:
            print("No assignments found in this course.")
    
    # Messaging operations
    if args.message_students:
        print(f"\n💬 Sending messages to students...")
        
        # Determine recipient emails
        if args.emails:
            student_emails = [email.strip() for email in args.emails.split(',')]
            print(f"📧 Targeting specific students: {student_emails}")
        else:
            # Get all students from the course (this would require additional API call)
            print("📧 Targeting all course students...")
            # For demo, use a sample list - in real implementation, you'd get from course enrollment
            student_emails = ['stephanie.cox@mcp.com', 'james.thomas30@mcp.com']
            print(f"   Using sample students: {student_emails}")
        
        stats = canvas.batch_message_students(
            student_emails=student_emails,
            subject=args.subject,
            body=args.body,
            course_id=args.course_id
        )
        
        print(f"\n📊 Messaging completed: {stats['successful']}/{stats['total']} messages sent")
    
    if args.get_conversations:
        if not args.email:
            print("❌ Error: --email is required for conversation lookup")
            return 1
        
        print(f"\n💬 Getting conversations with {args.email}...")
        
        # Find user by email
        user = canvas.find_user_by_email(args.email)
        if not user:
            print(f"❌ User not found: {args.email}")
            return 1
        
        conversations = canvas.get_conversation_with_user(user['id'])
        
        if conversations:
            print(f"Found {len(conversations)} conversations:")
            for conv in conversations:
                subject = conv.get('subject', 'No subject')
                last_message = conv.get('last_message', 'No message')
                print(f"   - {subject}")
                print(f"     Last: {last_message}")
        else:
            print("No conversations found with this user.")
    
    print(f"\n🎉 Operations completed successfully!")
    return 0


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)