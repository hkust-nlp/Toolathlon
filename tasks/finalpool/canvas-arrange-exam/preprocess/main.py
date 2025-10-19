#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas Exam Environment Preprocessing Main Script
Performs course setup and email injection functions
"""

import asyncio
import sys
from pathlib import Path
from argparse import ArgumentParser

# Add current directory to Python path for correct module imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import local modules
from setup_courses_with_mcp import main as setup_courses_main
from send_exam_notification_smtp import inject_exam_emails_from_config
from datetime import datetime

async def main(agent_workspace=None, launch_time=None):
    """Main function for preprocessing"""
    try:
        print("🚀 Starting Canvas exam environment preprocessing...")

        # # 0. Delete courses
        # DO NOT DELETE COURSES!!!
        # print("\n📚 Step 0: Delete courses...")
        # await setup_courses_main(delete=True, agent_workspace=agent_workspace)
        
        # 1. Create courses
        print("\n📚 Step 1: Create courses...")
        await setup_courses_main(agent_workspace=agent_workspace)
        
        # 2. Publish courses
        print("\n📢 Step 2: Publish courses...")
        # Call with publish mode, pass agent_workspace param
        await setup_courses_main(publish=True, agent_workspace=agent_workspace)

        exit(0)
        
        # 3. Inject exam notification emails
        print("\n📧 Step 3: Inject exam notification emails...")
        # Set email time to Jan 1, 2025, 10:00 AM (during final exam preparation)
        email_time = datetime(2025, 1, 1, 10, 0, 0)
        email_timestamp = email_time.timestamp()
        print(f"⏰ Email time set to: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Config file path
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        # Inject email into inbox
        email_success = inject_exam_emails_from_config(str(config_file), email_timestamp, clear_inbox=True, add_distractions=True)
        if not email_success:
            print("⚠️ Email injection failed, but will continue with next steps.")
        else:
            print("✅ Exam notification email injection succeeded.")
        
        print("\n🎉 Canvas exam environment preprocessing complete!")
        
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

