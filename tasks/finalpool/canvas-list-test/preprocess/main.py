#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Script for Canvas Exam Environment Preprocessing
Handles course setup and notification functionality
"""

import asyncio
import sys
import json
import random
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta

random.seed(42)

# Add current directory to Python path to ensure local modules can be imported
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import local modules
from setup_courses_with_mcp import run_with_args as setup_courses_main
from extract_quiz_info import parse_quiz_data, parse_assign_data
# from send_exam_notification_smtp import main as send_email_main

def update_course_due_dates():
    """Update 'due_at' of each course in course_config.json to about 1 week from now, randomizing within a week."""
    try:
        # Get path to course_config.json
        config_file_path = current_dir.parent / 'files' / 'course_config.json'
        
        print(f"📅 Starting to update course due dates...")
        print(f"📁 Config file path: {config_file_path}")
        
        # Check file existence
        if not config_file_path.exists():
            print(f"❌ Error: Config file does not exist - {config_file_path}")
            return False
        
        # Create a backup
        backup_path = config_file_path.with_suffix('.json.backup')
        with open(config_file_path, 'r', encoding='utf-8') as src, \
             open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print(f"💾 Backup created at: {backup_path}")
        
        # Load existing config
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Get current timestamp
        current_time = datetime.now()
        print(f"⏰ Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        updated_courses = 0
        random.seed(42)

        # Process all courses
        for course in config_data.get('courses', []):
            course_name = course.get('name', 'Unknown')
            course_code = course.get('course_code', 'Unknown')
            
            # Generate random due time (7-14 days from now)
            base_days = 7
            random_days = random.randint(0, 7)        # 0–7 days random offset
            random_hours = random.randint(0, 23)      # 0–23 hours random offset
            
            due_date = current_time + timedelta(days=base_days + random_days, hours=random_hours)
            # Set time to 23:59:00 that day
            due_date = due_date.replace(hour=23, minute=59, second=0, microsecond=0)
            due_date_str = due_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"📚 Updating course {course_code} ({course_name}):")
            
            # Update quiz due date
            if 'quiz' in course and course['quiz']:
                old_quiz_due = course['quiz'].get('due_at', 'N/A')
                course['quiz']['due_at'] = due_date_str
                print(f"  📝 Quiz due date: {old_quiz_due} → {due_date_str}")
            
            # Update assignment due date
            if 'assignment' in course and course['assignment']:
                old_assignment_due = course['assignment'].get('due_at', 'N/A')
                # Assignment due date is 1–3 days after quiz
                assignment_days_offset = random.randint(1, 3)
                assignment_due_date = due_date + timedelta(days=assignment_days_offset)
                assignment_due_date_str = assignment_due_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                course['assignment']['due_at'] = assignment_due_date_str
                print(f"  📋 Assignment due date: {old_assignment_due} → {assignment_due_date_str}")
            
            updated_courses += 1
        
        # Write updated data back to file
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully updated due dates for {updated_courses} courses")
        print(f"💾 Config file saved: {config_file_path}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: Config file not found: {config_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error: JSON format error - {e}")
        return False
    except Exception as e:
        print(f"❌ An error occurred while updating due dates: {e}")
        return False

def update_csv_files():
    """Update quiz and assignment info CSV files."""
    try:
        # Get course_config.json path
        config_file_path = current_dir.parent / 'files' / 'course_config.json'
        
        # Groundtruth workspace paths
        groundtruth_path = current_dir.parent / 'groundtruth_workspace'
        quiz_csv_path = groundtruth_path / 'quiz_info.csv'
        assignment_csv_path = groundtruth_path / 'assignment_info.csv'
        
        print(f"📝 Start updating CSV files...")
        print(f"📁 Config file path: {config_file_path}")
        print(f"📍 Output directory: {groundtruth_path}")
        print(f"📊 Quiz CSV output path: {quiz_csv_path}")
        print(f"📋 Assignment CSV output path: {assignment_csv_path}")
        
        # Ensure output directory exists
        groundtruth_path.mkdir(parents=True, exist_ok=True)
        
        # Update quiz info CSV
        print("📝 Updating quiz info CSV...")
        quiz_count = parse_quiz_data(str(config_file_path), str(quiz_csv_path))
        print(f"✅ Successfully updated quiz info, total {quiz_count} quizzes")
        
        # Update assignment info CSV
        print("📋 Updating assignment info CSV...")
        assignment_count = parse_assign_data(str(config_file_path), str(assignment_csv_path))
        print(f"✅ Successfully updated assignment info, total {assignment_count} assignments")
        
        print(f"📊 CSV file update finished:")
        print(f"  - Quiz info: {quiz_csv_path}")
        print(f"  - Assignment info: {assignment_csv_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ An error occurred while updating CSV files: {e}")
        return False

async def main(agent_workspace=None, launch_time=None):
    """Main Entry Point"""
    try:
        print("🚀 Starting Canvas exam environment preprocessing...")
        
        # 0. First, update course config's due dates
        print("\n📅 Step 1: Update course due dates")
        if not update_course_due_dates():
            print("❌ Due date update failed. Exiting.")
            sys.exit(1)
        
        # 1.5. Update CSV files
        print("\n📊 Step 2: Update quiz and assignment info CSV files")
        if not update_csv_files():
            print("❌ CSV file update failed. Exiting.")
            sys.exit(1)
        
        print("\n📚 Step 3: Create and publish courses automatically...")
    
        # Now course creation automatically publishes – no separate publish step needed

        # 2. Delete only this task's configured courses. Matching requires both
        # exact name and exact course_code; unrelated Canvas courses are preserved.
        print("\n🗑️ Step 4: Delete existing configured courses")
        cleanup_success = await setup_courses_main(delete=True, agent_workspace=agent_workspace)
        if not cleanup_success:
            print("❌ Configured-course cleanup failed. Exiting.")
            sys.exit(1)

        # 3. Create and publish new courses
        print("\n✨ Step 5: Create new courses")
        setup_success = await setup_courses_main(agent_workspace=agent_workspace)
        if not setup_success:
            print("❌ Configured-course setup failed. Exiting.")
            sys.exit(1)

        # 4. Submit assignments
        print("\n📝 Step 6: Submit student assignments")
        submission_success = await setup_courses_main(
            submit_assignments=True,
            agent_workspace=agent_workspace,
        )
        if not submission_success:
            print("❌ Assignment submission setup failed. Exiting.")
            sys.exit(1)

        print("\n🎉 Canvas exam environment preprocessing completed!")
        print("✅ All courses are created and published")
        print("✅ Course due dates have been updated to be about a week in the future")
        print("✅ Quiz and assignment info CSV files have been updated")
        print("✅ Student assignments have been submitted automatically")

    except Exception as e:
        print(f"❌ An error occurred during preprocessing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Run async main function
    asyncio.run(main(agent_workspace=args.agent_workspace, launch_time=args.launch_time))
