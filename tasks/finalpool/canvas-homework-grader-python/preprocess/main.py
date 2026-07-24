#!/usr/bin/env python3
"""
Canvas Homework Grader Task - Main Preprocess Pipeline
This script orchestrates the complete preprocessing workflow:
1. Clear existing emails from inbox  
2. Generate new inbox with homework submissions
3. Import emails to MCP server
4. Set up Canvas course and assignments
"""

import asyncio
import subprocess
import sys
import json
import csv
from argparse import ArgumentParser
from pathlib import Path
from time import sleep


def run_command(command, description="", check=True, shell=True):
    """Run a command and handle output"""
    print(f"🔧 {description}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stdout:
            print(f"   Stdout: {e.stdout}")
        if e.stderr:
            print(f"   Stderr: {e.stderr}")
        if check:
            raise
        return e


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
    return None


def load_email_config(config_file_path):
    """Load email configuration from JSON file"""
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading email config: {e}")
        return None


def clear_inbox(teacher_info, email_config):
    """Clear all emails from the inbox using poste ops clear_folder function"""
    print("\n🗑️  Step 1: Clearing existing emails from inbox")
    print("=" * 50)
    
    try:
        # Add the utils path for import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent  # canvas-homework-grader-python
        finalpool_dir = task_dir.parent  # finalpool
        tasks_dir = finalpool_dir.parent  # tasks
        toolathlon_root = tasks_dir.parent  # toolathlon
        utils_dir = toolathlon_root / "utils"
        
        sys.path.insert(0, str(utils_dir))
        from app_specific.poste.ops import clear_folder
        
        # Prepare IMAP configuration for clear_folder function
        imap_config = {
            "email": teacher_info['email'],
            "password": teacher_info['password'],
            "imap_server": email_config.get('imap_server', 'localhost'),
            "imap_port": email_config.get('imap_port', 993),
            "use_ssl": email_config.get('use_ssl', True),
            "use_starttls": email_config.get('use_starttls', False)
        }
        
        print(f"🔧 Clearing inbox for: {teacher_info['email']}")
        
        # Clear the INBOX folder
        clear_folder("INBOX", imap_config)
        
        print("✅ Inbox clearing completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear inbox: {e}")
        print("💡 Continuing with preprocessing anyway...")
        return False


def generate_inbox():
    """Generate new inbox with homework submissions and fake emails"""
    print("\n📧 Step 2: Generating new inbox with homework submissions")
    print("=" * 50)
    
    script_dir = Path(__file__).parent
    generate_script = script_dir / "generate_inbox.py"
    
    if not generate_script.exists():
        print(f"❌ Generate script not found: {generate_script}")
        return False
    
    try:
        result = run_command(
            f"python {generate_script}",
            "Generating inbox with homework submissions and fake emails"
        )
        print("✅ Inbox generation completed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Inbox generation failed")
        return False


def import_emails():
    """Import generated emails to MCP server using import_emails.py"""
    print("\n📥 Step 3: Importing emails to MCP server")
    print("=" * 50)
    
    script_dir = Path(__file__).parent
    import_script = script_dir / "import_emails.py"
    
    if not import_script.exists():
        print(f"❌ Import script not found: {import_script}")
        return False
    
    # Get the generated inbox path
    base_dir = script_dir.parent
    inbox_path = base_dir / "files" / "generated_inbox.json"
    
    if not inbox_path.exists():
        print(f"❌ Generated inbox file not found: {inbox_path}")
        return False
    
    print(f"📧 Importing {inbox_path.name}...")
    
    # Run the import script directly using Python
    try:
        result = run_command(
            f"python {import_script} --target-folder INBOX --preserve-folders",
            "Importing emails to MCP server",
            check=False  # Don't fail if import has issues
        )
        
        # Check if the command was successful - look for success indicators
        if result.returncode == 0:
            print("✅ Email import completed successfully")
            return True
        else:
            print("❌ Email import failed - MCP server may not be available")
            print("💡 Manual MCP Tool Call Required:")
            print(f"   Tool: import_emails (from emails MCP server)")
            print(f"   Arguments:")
            print(f"     - import_path: {inbox_path}")
            print(f"     - target_folder: INBOX")
            print(f"     - preserve_folders: true")
            return False
            
    except Exception as e:
        print(f"❌ Error running import script: {e}")
        print("💡 Manual MCP Tool Call Required:")
        print(f"   Tool: import_emails (from emails MCP server)")
        print(f"   Arguments:")
        print(f"     - import_path: {inbox_path}")
        print(f"     - target_folder: INBOX")
        print(f"     - preserve_folders: true")
        return False


def reinitialize_course(canvas_api, canvas_utils, course_id, teacher_info, email_config):
    """
    Reinitialize an existing CS5123 course with fresh content
    
    Args:
        canvas_api: CanvasAPI instance
        canvas_utils: Canvas utils instance
        course_id: Existing course ID to reinitialize
        teacher_info: Teacher information dict
        email_config: Email configuration dict
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"🔄 Reinitializing course {course_id}...")
        
        # Step 1: Clear existing assignments
        print("   📝 Clearing existing assignments...")
        try:
            assignments = canvas_api.list_assignments(course_id)
            if assignments:
                for assignment in assignments:
                    assignment_id = assignment.get('id')
                    assignment_name = assignment.get('name', 'Unknown')
                    # Delete assignment (Canvas API usually supports this)
                    delete_result = canvas_api._make_request('DELETE', f'courses/{course_id}/assignments/{assignment_id}')
                    if delete_result:
                        print(f"      ✅ Deleted assignment: {assignment_name}")
                    else:
                        print(f"      ⚠️  Could not delete assignment: {assignment_name}")
                print(f"   ✅ Processed {len(assignments)} existing assignments")
            else:
                print("   ✅ No existing assignments to clear")
        except Exception as e:
            print(f"   ⚠️  Error clearing assignments: {e}")
        
        # Step 2: Update course enrollments (add teacher if needed)
        print("   👨‍🏫 Checking teacher enrollment...")
        try:
            teacher_email = teacher_info['email']
            enrollments = canvas_api.get_course_enrollments(course_id)
            
            # Check if teacher is already enrolled
            teacher_enrolled = False
            for enrollment in enrollments:
                if (enrollment.get('type') == 'TeacherEnrollment' and
                    enrollment.get('user', {}).get('email') == teacher_email):
                    teacher_enrolled = True
                    print(f"      ✅ Teacher {teacher_info['name']} already enrolled")
                    break
            
            if not teacher_enrolled:
                # Add teacher to course
                if canvas_utils.add_user_to_course_by_email(course_id, teacher_email, 'TeacherEnrollment'):
                    print(f"      ✅ Added {teacher_info['name']} as teacher")
                else:
                    print(f"      ⚠️  Could not add teacher {teacher_email}")
                    
        except Exception as e:
            print(f"   ⚠️  Error managing teacher enrollment: {e}")
        
        # Step 3: Enroll students from CSV
        print("   👥 Managing student enrollments...")
        try:
            script_dir = Path(__file__).parent
            student_csv = script_dir / "student_list.csv"
            
            if student_csv.exists():
                # Get current student enrollments
                current_students = set()
                enrollments = canvas_api.get_course_enrollments(course_id)
                for enrollment in enrollments:
                    if enrollment.get('type') == 'StudentEnrollment':
                        user = enrollment.get('user', {})
                        if user.get('email'):
                            current_students.add(user['email'])
                
                print(f"      📊 Found {len(current_students)} currently enrolled students")
                
                # Define specific student indices to match the homework grading task
                selected_student_indices = [0, 1, 2, 3, 4, 5]  # First 6 students
                
                enrollment_stats = canvas_utils.batch_enroll_users_from_csv(
                    course_id=course_id,
                    csv_file=student_csv,
                    role='StudentEnrollment',
                    selected_indices=selected_student_indices
                )
                
                print(f"      ✅ Student enrollment result: {enrollment_stats['successful']} successful, {enrollment_stats['failed']} failed")
                if enrollment_stats['successful'] != len(selected_student_indices):
                    print(f"      ❌ Only enrolled {enrollment_stats['successful']}/{len(selected_student_indices)} students")
                    return False
            else:
                print("      ⚠️  Student CSV file not found")
        except Exception as e:
            print(f"   ⚠️  Error managing student enrollments: {e}")
        
        # Step 4: Create homework2 assignment
        print("   📝 Creating homework2 assignment...")
        try:
            assignment = canvas_api.create_assignment(
                course_id=course_id,
                name="homework2",
                description="Two Sum Problem - Submit your Python solution",
                points_possible=10,
                published=True
            )
            
            if assignment:
                print(f"      ✅ Created assignment: homework2 (ID: {assignment['id']}, 10 points)")
            else:
                print("      ❌ Failed to create homework2 assignment")
                return False
        except Exception as e:
            print(f"   ❌ Error creating assignment: {e}")
            return False
        
        # Step 5: Ensure course is published
        print("   📤 Ensuring course is published...")
        try:
            if canvas_api.publish_course(course_id):
                print("      ✅ Course is published")
            else:
                print("      ⚠️  Course publish status uncertain")
        except Exception as e:
            print(f"   ⚠️  Error publishing course: {e}")
        
        print(f"✅ Course {course_id} reinitialization completed!")
        
        # Get canvas_url from canvas_api or construct it
        canvas_url = getattr(canvas_api, 'base_url', 'http://localhost:10001')
        print(f"🎯 Canvas course URL: {canvas_url}/courses/{course_id}")
        
        # Extract student IDs after successful course reinitialization
        print("\n🆔 Extracting student IDs after reinitialization...")
        try:
            script_dir = Path(__file__).parent
            extract_script = script_dir / "extract_student_ids.py"
            if extract_script.exists():
                import subprocess
                result = subprocess.run(
                    ["python", str(extract_script), "--course-id", str(course_id)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("✅ Student ID extraction completed")
                else:
                    print("⚠️  Student ID extraction failed")
            else:
                print("⚠️  Extract script not found")
        except Exception as e:
            print(f"⚠️  Error extracting student IDs: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Course reinitialization failed: {e}")
        return False


def setup_canvas(teacher_info, email_config):
    """Set up Canvas course with students and assignments using Canvas utils"""
    print("\n🎓 Step 4: Setting up Canvas course")
    print("=" * 50)
    
    try:
        # Add the utils path for import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent  # canvas-homework-grader-python
        finalpool_dir = task_dir.parent  # finalpool
        tasks_dir = finalpool_dir.parent  # tasks
        toolathlon_root = tasks_dir.parent  # toolathlon
        utils_dir = toolathlon_root / "utils"
        
        sys.path.insert(0, str(utils_dir))
        from app_specific.canvas import create_canvas_utils, CanvasAPI
        
        # Get Canvas configuration - try multiple sources
        canvas_url = None
        canvas_token = None
        
        # First try teacher CSV canvas_token
        if teacher_info.get('canvas_token'):
            canvas_token = teacher_info['canvas_token']
        
        # Try to load from token_key_session.py
        try:
            base_dir = script_dir.parent
            sys.path.insert(0, str(base_dir))
            from token_key_session import all_token_key_session
            canvas_url = f"http://localhost:10001"
            canvas_token = all_token_key_session.admin_canvas_api_token
            # canvas_token = canvas_token or all_token_key_session.canvas_api_token
        except ImportError as e:
            raise ValueError("Faile to import canvas token/key")
            canvas_url = "http://localhost:10001"
            canvas_token = canvas_token or "mcpcanvasadmintoken1"
        
        print(f"🔧 Canvas URL: {canvas_url}")
        
        # Create Canvas API instance
        canvas_api = CanvasAPI(canvas_url, canvas_token)
        
        # Test connection
        current_user = canvas_api.get_current_user()
        if not current_user:
            print("❌ Failed to connect to Canvas")
            return False
        
        print(f"✅ Connected to Canvas as: {current_user.get('name', 'Unknown')}")
        
        # Create Canvas utils
        canvas_utils = create_canvas_utils(
            task_dir=str(script_dir.parent),
            canvas_url=canvas_url,
            canvas_token=canvas_token
        )
        
        # First, check if CS5123 course already exists and reinitialize it
        print("🔍 Checking for existing CS5123 Programming Fundamentals course...")
        try:
            # Get all courses to find existing CS5123 course
            all_courses = canvas_api.list_courses(include_deleted=True, account_id=1)
            existing_cs5123_course = None
            
            if all_courses:
                for course in all_courses:
                    course_name = course.get('name', '')
                    course_code = course.get('course_code', '')
                    
                    # Check if it's a CS5123 course
                    if (course_code == 'CS5123'):
                        existing_cs5123_course = course
                        break
                
                if existing_cs5123_course:
                    course_id = existing_cs5123_course['id']
                    course_name = existing_cs5123_course.get('name', 'CS5123')
                    print(f"✅ Found existing CS5123 course: {course_name} (ID: {course_id})")
                    print("🔄 Reinitializing existing course instead of creating new one...")
                    
                    # Reinitialize the existing course
                    success = reinitialize_course(canvas_api, canvas_utils, course_id, teacher_info, email_config)
                    if success:
                        print(f"✅ Successfully reinitialized course: {course_name}")
                        return True
                    else:
                        print(f"❌ Failed to reinitialize course: {course_name}")
                        print("💡 Falling back to creating new course...")
                        # Continue to create new course
                else:
                    print("✅ No existing CS5123 course found - will create new one")
            else:
                print("⚠️  Could not retrieve courses list - will create new course")
        except Exception as e:
            print(f"⚠️  Error checking for existing courses: {e}")
            print("💡 Continuing with new course creation...")
        
        print("🏗️  Creating CS5123 Programming Fundamentals course...")
        
        # Create course
        course = canvas_utils.create_course_with_config(
            course_name="CS5123 Programming Fundamentals",
            course_code="CS5123",
            account_id=1,
            syllabus_body="Two Sum Problem homework assignment course"
        )
        
        if not course:
            print("❌ Failed to create course")
            return False
        
        course_id = course['id']
        print(f"✅ Course created: CS5123 Programming Fundamentals (ID: {course_id})")
        
        # Add teacher to course (current user)
        try:
            teacher_email = teacher_info['email']
            if canvas_utils.add_user_to_course_by_email(course_id, teacher_email, 'TeacherEnrollment'):
                print(f"✅ Added {teacher_info['name']} as teacher")
            else:
                print(f"⚠️  Could not add teacher {teacher_email} (may already be enrolled)")
        except Exception as e:
            print(f"⚠️  Error adding teacher: {e}")
        
        # Enroll students from CSV
        student_csv = script_dir / "student_list.csv"
        if student_csv.exists():
            print("👥 Enrolling students from student_list.csv...")
            
            # Define specific student indices to match the homework grading task
            selected_student_indices = [0, 1, 2, 3, 4, 5]  # First 6 students
            
            enrollment_stats = canvas_utils.batch_enroll_users_from_csv(
                course_id=course_id,
                csv_file=student_csv,
                role='StudentEnrollment',
                selected_indices=selected_student_indices
            )
            
            if enrollment_stats['successful'] == len(selected_student_indices):
                print(f"✅ Enrolled {enrollment_stats['successful']} students")
            else:
                print(f"❌ Only enrolled {enrollment_stats['successful']}/{len(selected_student_indices)} students")
                return False
        else:
            print("⚠️  Student CSV file not found, skipping enrollment")
        
        # Create homework2 assignment
        print("📝 Creating homework2 assignment...")
        try:
            assignment = canvas_api.create_assignment(
                course_id=course_id,
                name="homework2",
                description="Two Sum Problem - Submit your Python solution",
                points_possible=10,
                published=True
            )
            
            if assignment:
                print(f"✅ Created assignment: homework2 (ID: {assignment['id']}, 10 points)")
            else:
                print("❌ Failed to create homework2 assignment")
                return False
        except Exception as e:
            print(f"❌ Error creating assignment: {e}")
            return False
        
        # Publish course
        print("📤 Publishing course...")
        try:
            if canvas_api.publish_course(course_id):
                print("✅ Course published successfully")
            else:
                print("⚠️  Course publish status uncertain")
        except Exception as e:
            print(f"⚠️  Error publishing course: {e}")
        
        print(f"🎯 Canvas setup completed!")
        print(f"   Course URL: {canvas_url}/courses/{course_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Canvas setup failed: {e}")
        return False


def extract_student_ids(args):
    """Extract Canvas student IDs after course setup"""
    print("\n🆔 Step 5: Extracting Canvas student IDs")
    print("=" * 50)
    
    script_dir = Path(__file__).parent
    extract_script = script_dir / "extract_student_ids.py"
    
    if not extract_script.exists():
        print(f"❌ Extract script not found: {extract_script}")
        return False
    
    try:
        result = run_command(
            f"python {extract_script} --output {args.agent_workspace}/student_canvas_ids.csv",
            "Extracting Canvas student IDs and saving to CSV"
        )
        print("✅ Student ID extraction completed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Student ID extraction failed")
        return False




def main():
    """Main preprocessing pipeline"""
    parser = ArgumentParser(description="Canvas Homework Grader Preprocessing Pipeline")
    parser.add_argument("--agent_workspace", required=False,
                       help="Agent workspace directory")
    parser.add_argument("--credentials_file", default="configs/credentials.json",
                       help="Credentials file path")
    parser.add_argument("--launch_time", nargs='*', required=False, 
                       help="Launch time (can contain spaces)")
    parser.add_argument("--skip-clear", action="store_true",
                       help="Skip clearing existing emails")
    parser.add_argument("--skip-canvas", action="store_true", 
                       help="Skip Canvas setup")
    parser.add_argument("--canvas-only", action="store_true",
                       help="Only run Canvas setup, skip email processing")
    parser.add_argument("--emails-only", action="store_true",
                       help="Only run email processing, skip Canvas setup")
    
    args = parser.parse_args()
    
    print("🎯 Canvas Homework Grader - Preprocessing Pipeline")
    print("=" * 70)
    print("This pipeline will set up the complete environment for homework grading:")
    print("  📧 Email environment with homework submissions")  
    print("  🎓 Canvas course with students and assignments")
    print("  📝 Ready for agent to grade homework2 submissions")
    print()
    
    # Load configuration files
    script_dir = Path(__file__).parent
    teacher_csv = script_dir / "teacher_list.csv"
    email_config_file = script_dir.parent / "email_config.json"
    
    teacher_info = load_teacher_info(teacher_csv)
    email_config = load_email_config(email_config_file)
    
    if not teacher_info:
        print("❌ Failed to load teacher information")
        sys.exit(1)
    
    if not email_config:
        print("❌ Failed to load email configuration") 
        sys.exit(1)
    
    print(f"👨‍🏫 Teacher: {teacher_info['name']} ({teacher_info['email']})")
    print(f"📧 Email server: {email_config.get('smtp_server', 'N/A')}:{email_config.get('smtp_port', 'N/A')}")
    
    success_count = 0
    total_steps = 5  # Updated to include student ID extraction
    
    # Canvas-only mode
    if args.canvas_only:
        print("\n🎓 Canvas-only mode - skipping email setup")
        if setup_canvas(teacher_info, email_config):
            # Also extract student IDs in canvas-only mode
            extract_student_ids(args)
            print("\n🎉 Canvas-only setup completed successfully!")
        else:
            print("\n❌ Canvas-only setup failed")
            sys.exit(1)
        return
    
    # Emails-only mode
    if args.emails_only:
        print("\n📧 Emails-only mode - skipping Canvas setup")
        steps_success = 0
        
        if not args.skip_clear:
            if clear_inbox(teacher_info, email_config):
                steps_success += 1
        else:
            print("\n⏭️  Skipping inbox clearing")
            steps_success += 1
        
        if generate_inbox():
            steps_success += 1
            
        if import_emails():
            steps_success += 1
            
        if steps_success >= 2:
            print("\n🎉 Emails-only setup completed successfully!")
        else:
            print("\n❌ Emails-only setup failed")
            sys.exit(1)
        return
    
    # Full pipeline mode
    # Step 1: Clear inbox (optional)
    if not args.skip_clear:
        if clear_inbox(teacher_info, email_config):
            success_count += 1
        sleep(1)
    else:
        print("\n⏭️  Skipping inbox clearing")
        success_count += 1
    
    # Step 2: Generate inbox
    if generate_inbox():
        success_count += 1
    else:
        print("❌ Failed to generate inbox - aborting")
        sys.exit(1)
    
    sleep(1)
    
    # Step 3: Import emails  
    if import_emails():
        success_count += 1
    else:
        print("❌ Email import failed - MCP server may be needed for manual import - aborting")
        sys.exit(1)
    
    sleep(2)
    
    # Step 4: Canvas setup (optional)
    if not args.skip_canvas:
        if setup_canvas(teacher_info, email_config):
            success_count += 1
            # Step 5: Extract student IDs
            if extract_student_ids(args):
                success_count += 1
            else:
                print("❌ Student ID extraction failed - aborting")
                sys.exit(1)
        else:
            print("❌ Canvas setup failed - aborting")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping Canvas setup")
        success_count += 2  # Count both Canvas setup and student ID extraction as success if skipped
    
    # Final summary
    print("\n🎉 Preprocessing Pipeline Summary")
    print("=" * 50)
    print(f"✅ Steps completed: {success_count}/{total_steps}")
    
    if success_count >= 2:  # At least inbox generation worked
        print("🎯 Environment ready for Canvas homework grading!")
        print(f"📧 Teacher inbox: {teacher_info['email']}")
        print("📝 Expected homework2 submissions from 6 students:")
        print("   - Timothy Ruiz (2 submissions - use latest)")
        print("   - Martha Watson (syntax error)")
        print("   - Donald Richardson (runtime error)")
        print("   - Shirley Rodriguez (correct solution)")
        print("   - Alice Ward (logic error)")
        print("   - Frank Phillips (import error)")
        print("\n💡 Next step: Run the Canvas homework grader agent!")
        
        # Show MCP tool calls that may still need to be made
        if success_count < 3:
            print("\n🔧 MCP Tool Calls (may be required):")
            print("1. Import emails: import_emails with generated_inbox.json (emails MCP)")
        
    else:
        print("❌ Setup incomplete - critical steps failed")
        sys.exit(1)


if __name__ == "__main__":
    main()