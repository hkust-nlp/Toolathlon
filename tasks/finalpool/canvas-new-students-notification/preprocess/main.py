#!/usr/bin/env python3
"""
Canvas Notification Task Preprocessing

This module sets up Canvas environment for the notification task using
the centralized utils.app_specific.canvas utility functions.
"""

import sys
import argparse
import asyncio
import json
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


async def delete_courses_via_mcp(target_course_names):
    """
    Delete specified courses using MCP canvas server

    This function will:
    1. Connect to canvas MCP server
    2. List all courses in the account
    3. Delete only the courses whose names match target_course_names

    :param target_course_names: List of course names to delete (required).
    """
    print(f"🗑️ Starting to delete {len(target_course_names)} specified courses via Canvas MCP...")

    try:
        # Add the utils path for MCPServerManager import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent  # canvas-notification-python
        finalpool_dir = task_dir.parent  # finalpool
        tasks_dir = finalpool_dir.parent  # tasks
        toolathlon_root = tasks_dir.parent  # toolathlon

        sys.path.insert(0, str(toolathlon_root))
        from utils.mcp.tool_servers import MCPServerManager

        print(f"🚀 Attempting to connect to Canvas MCP server...")

        # Load local token_key_session from task directory
        local_token_key_session = None
        token_key_session_path = task_dir / "token_key_session.py"

        if token_key_session_path.exists():
            print(f"🔑 Loading task-specific token configuration from {token_key_session_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("token_key_session", token_key_session_path)
            token_key_session_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(token_key_session_module)
            local_token_key_session = token_key_session_module.all_token_key_session
        else:
            print("⚠️  No task-specific token configuration found, using global defaults")

        # Set up temporary workspace
        workspace = script_dir / "temp_workspace"
        workspace.mkdir(exist_ok=True)

        # Initialize MCP Server Manager with local token configuration
        server_manager = MCPServerManager(
            agent_workspace=str(workspace),
            config_dir=str(toolathlon_root / "configs" / "mcp_servers"),
            debug=False,
            local_token_key_session=local_token_key_session
        )

        # Connect to canvas server specifically
        await server_manager.connect_servers(["canvas"])
        connected_names = server_manager.get_connected_server_names()

        if "canvas" not in connected_names:
            print("❌ Failed to connect to canvas MCP server")
            return False

        print(f"✅ Connected to canvas MCP server")

        canvas_server = server_manager.connected_servers["canvas"]

        # First, try to get all courses from account (admin view)
        print("🔍 Fetching all courses from account...")
        try:
            account_courses_result = await canvas_server.call_tool("canvas_list_account_courses", {"account_id": 1})
            courses = []

            # Parse the result to extract courses
            if hasattr(account_courses_result, 'content'):
                for content in account_courses_result.content:
                    if hasattr(content, 'text'):
                        try:
                            courses = json.loads(content.text)
                        except:
                            print(f"Could not parse account courses: {content.text}")

            # If account courses didn't work, try user courses
            if not courses:
                print("🔍 Trying to fetch user courses...")
                user_courses_result = await canvas_server.call_tool("canvas_list_courses", {})
                if hasattr(user_courses_result, 'content'):
                    for content in user_courses_result.content:
                        if hasattr(content, 'text'):
                            try:
                                courses = json.loads(content.text)
                            except:
                                print(f"Could not parse user courses: {content.text}")

        except Exception as e:
            print(f"❌ Error fetching courses: {e}")
            courses = []

        if not courses:
            print("⚠️  No courses found to delete")
            await server_manager.disconnect_servers()
            return True

        print(f"📚 Found {len(courses)} total courses")
        print(f"🎯 Target courses to delete: {target_course_names}")

        # Filter courses to only include target courses
        courses_to_delete = []
        for course in courses:
            course_name = course.get('name', f'Course {course.get("id")}')
            if course_name in target_course_names:
                courses_to_delete.append(course)
                print(f"📚 Found target course to delete: {course_name}")
            else:
                print(f"⏩ Skipping course: {course_name} (not in target list)")

        if not courses_to_delete:
            print("⚠️  No matching courses found to delete")
            await server_manager.disconnect_servers()
            return True

        print(f"📚 Will delete {len(courses_to_delete)} courses")

        # Delete each course
        deleted_count = 0
        failed_count = 0

        for course in courses_to_delete:
            course_id = course.get('id')
            course_name = course.get('name', f'Course {course_id}')

            print(f"🗑️ Deleting course {course_id}: {course_name}")

            try:
                delete_result = await canvas_server.call_tool("canvas_delete_course", {"course_id": course_id})

                # Check if deletion was successful
                success = False
                if hasattr(delete_result, 'content'):
                    for content in delete_result.content:
                        if hasattr(content, 'text'):
                            print(f"   📄 {content.text}")
                            if "deleted" in content.text.lower() or "concluded" in content.text.lower():
                                success = True
                        else:
                            print(f"   📄 {content}")

                if success:
                    print(f"   ✅ Successfully deleted course {course_id}")
                    deleted_count += 1
                else:
                    print(f"   ⚠️ Deletion status unclear for course {course_id}")
                    deleted_count += 1  # Assume success if no error

            except Exception as e:
                print(f"   ❌ Failed to delete course {course_id}: {e}")
                failed_count += 1

        # Cleanup
        await server_manager.disconnect_servers()

        print(f"\n📊 Deletion Summary:")
        print(f"   ✅ Successfully deleted: {deleted_count} courses")
        print(f"   ❌ Failed to delete: {failed_count} courses")
        print(f"   📚 Total processed: {len(courses)} courses")

        if failed_count == 0:
            print("✅ All courses deleted successfully")
            return True
        else:
            print(f"⚠️ {failed_count} courses failed to delete")
            return False

    except ImportError as ie:
        print(f"❌ Could not import MCP utilities: {ie}")
        return False
    except Exception as e:
        print(f"❌ Error during course deletion: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
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
    
    print("Canvas Course Preprocessing - Introduction to AI-8")
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
        print(f"Task: Set up 'Introduction to AI-8' course")
        if args.agent_workspace:
            print(f"Agent workspace: {args.agent_workspace}")
        
        print(f"Connected to Canvas as: {current_user.get('name', 'Unknown')}")
        
        # Step 1: MCP-based cleanup for "Introduction to AI-8" courses
        if args.cleanup:
            print("\nCleaning up Canvas environment using MCP...")

            # Use MCP to delete "Introduction to AI-8" courses specifically
            target_courses = ["Introduction to AI-8"]
            print(f"📋 Target courses to delete: {target_courses}")

            try:
                success = await delete_courses_via_mcp(target_courses)
                if success:
                    print("✅ MCP course deletion completed successfully")
                else:
                    print("⚠️ MCP course deletion completed with some issues")
            except Exception as e:
                print(f"❌ Error during MCP course deletion: {e}")
                print("💡 Continuing with preprocessing anyway...")

            # Also clean up conversations using original method
            print("Deleting all conversations...")
            deleted_conversations = canvas_utils.cleanup_conversations()
            print(f"Cleanup complete: conversations deleted: {deleted_conversations}")
            print("Canvas environment is ready for fresh 'Introduction to AI-8' course setup")
        
        # Step 2: Create course
        print("\nStep: Create Course")
        course = canvas_utils.create_course_with_config(
            course_name="Introduction to AI-8",
            course_code="AI101",
            account_id=1,
            is_public=True,
            is_public_to_auth_users=True,
            syllabus_body="Welcome to Introduction to AI-8!"
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
        print(f"Course: Introduction to AI-8 (ID: {course_id})")
        print(f"Course status: Published")
        print(f"Direct link: {canvas_utils.canvas.base_url}/courses/{course_id}")
        
        print("Canvas course setup completed! Course is ready for notification tasks.")
            
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())