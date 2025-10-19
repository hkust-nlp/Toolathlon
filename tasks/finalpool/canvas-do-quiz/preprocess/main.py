#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main script for Canvas environment preprocessing.
Handles course setup and email notification capabilities.
"""

import asyncio
import sys
from pathlib import Path
from argparse import ArgumentParser

# Add current directory to PYTHONPATH to ensure correct module import
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import local modules
from setup_courses_with_mcp import run_with_args as setup_courses_main
from update_dates import update_config_dates
# from send_exam_notification_smtp import main as send_email_main

async def main(agent_workspace=None, launch_time=None):
    """Main function"""
    try:
        print("🚀 Starting Canvas exam environment preprocessing...")
        
        # Update the course configuration dates to one day in the future
        config_path = current_dir.parent / "files" / "course_config.json"
        print(f"📅 Updating date fields in config file: {config_path}")
        update_config_dates(str(config_path))
        
        await setup_courses_main(agent_workspace=agent_workspace)
        
        print("\n🎉 Canvas environment preprocessing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error occurred during preprocessing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Run the asynchronous main function
    asyncio.run(main(agent_workspace=args.agent_workspace, launch_time=args.launch_time))

