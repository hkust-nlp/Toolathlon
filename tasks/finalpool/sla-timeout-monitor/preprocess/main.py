import argparse
import os
import asyncio
import sys
import json
import random
from rich import print
from utils.app_specific.poste.ops import clear_folder
from utils.general.helper import read_json

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: preprocess -> sla-timeout-monitor -> fan -> tasks -> toolathlon
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)
task_root = os.path.dirname(current_dir)

from . import create_snowflake_db

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent_workspace", type=str, required=True)
    parser.add_argument("--launch_time", type=str, required=True)
    parser.add_argument("--num_tickets", type=int, default=20, help="Number of support tickets to generate")
    parser.add_argument("--num_users", type=int, default=8, help="Number of users to generate")

    args = parser.parse_args()

    agent_workspace = args.agent_workspace
    launch_time = args.launch_time

    print(f"agent_workspace: {agent_workspace}")
    print(f"launch_time: {launch_time}")
    

    random.seed(42)
    
    # Step 1: Initialize Snowflake database with SLA monitoring schema and test data
    print("\n" + "="*60)
    print("PREPROCESSING STEP 1: Initialize Snowflake Database")
    print("="*60)
    print("📋 Database: SLA_MONITOR") 
    print("📋 Purpose: Customer Support SLA Timeout Monitoring System")
    print("📋 Tables: USERS, SUPPORT_TICKETS, SLA_CONFIGURATIONS")
    
    try:
        groundtruth_data = await create_snowflake_db.initialize_database()
        print("✅ Step 1 completed: Snowflake database initialization")
    except Exception as e:
        print(f"❌ Step 1 failed: Database initialization error - {e}")
        raise e

    
    # step 1.5
    gt_file = os.path.join(task_root, "groundtruth_workspace", "sla_monitoring.jsonl")
    os.makedirs(os.path.dirname(gt_file), exist_ok=True)
    with open(gt_file, 'w', encoding='utf-8') as f:
        for item in groundtruth_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"✅ Generated groundtruth file: {gt_file}")


    # step 2
    print("\n" + "="*60)
    print("PREPROCESSING STEP 2: Clear Emails")
    print("="*60)
    
    involved_emails_file = os.path.join(os.path.dirname(__file__), "..", "files", "involved_emails.json")
    involved_emails = read_json(involved_emails_file)
    for role in involved_emails:
        for email_address, config in involved_emails[role].items():
            full_config = {"email": email_address, **config}
            clear_folder("INBOX",full_config)
            clear_folder("Sent",full_config)
    
    print("✅ Step 2 completed: Emails cleared")

    print("\n" + "="*60)
    print("🎉 PREPROCESSING COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("✅ Snowflake database initialized with test data")
    print("✅ Ready for SLA timeout monitoring workflow")
    print("\n📋 Next steps:")
    print("  1. Monitor support tickets for SLA violations")
    print("  2. Generate timeout reports sorted by service level priority")
    print("  3. Send notification emails to support managers")
    print("  4. Send apology emails to affected customers")


if __name__ == "__main__":
    asyncio.run(main())