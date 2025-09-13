from argparse import ArgumentParser
import os
import sys
import json
from pathlib import Path
from google.oauth2 import service_account
from .ggcloud_clean_dataset import clean_dataset
from .ggcloud_upload import upload_transactions_data


def get_project_id(credentials_path):
    """Extract project ID from credentials JSON file"""
    try:
        with open(credentials_path, 'r') as f:
            data = json.load(f)
            return data.get("project_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    """Main preprocessing function for flagged-transactions task"""
    parser = ArgumentParser(description="Preprocess flagged-transactions data for BigQuery")
    parser.add_argument("--agent_workspace", required=True, help="Agent workspace directory")
    parser.add_argument("--credentials_file", required=False, 
                       default="configs/gcp-service_account.keys.json",
                       help="Path to Google Cloud credentials JSON file")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("=" * 60)
    print("FLAGGED TRANSACTIONS - BigQuery Preprocessing")
    print("=" * 60)
    
    # Get credentials file path
    credentials_path = Path(args.credentials_file)
    
    # Make sure the path is absolute
    if not credentials_path.is_absolute():
        credentials_path = Path.cwd() / credentials_path
    
    if not credentials_path.exists():
        print(f"❌ Credentials file not found: {credentials_path}")
        print("Please ensure the Google Cloud service account key file exists")
        sys.exit(1)

    try:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        print(f"✅ Loaded credentials from: {credentials_path}")
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        sys.exit(1)

    project_id = get_project_id(credentials_path)
    if not project_id:
        print("❌ Could not extract project_id from credentials file")
        sys.exit(1)
    
    print(f"🏗️  Using Google Cloud project: {project_id}")

    print("\n" + "=" * 50)
    print("STEP 1: Clean BigQuery Dataset")
    print("=" * 50)
    dataset = clean_dataset(project_id, credentials)
    
    if not dataset:
        print("❌ Failed to setup BigQuery dataset")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("STEP 2: Upload Transaction Data")
    print("=" * 50)
    success = upload_transactions_data(project_id, credentials)
    
    if success:
        print("\n🎉 Preprocessing completed successfully!")
        print(f"✅ Data is now available in BigQuery:")
        print(f"   Project: {project_id}")
        print(f"   Dataset: flagged_transactions")
        print(f"   Table: all_transactions_recordings")
        print(f"\n💡 You can now query the data using:")
        print(f"   SELECT * FROM `{project_id}.flagged_transactions.all_transactions_recordings` LIMIT 10")
    else:
        print("\n❌ Preprocessing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()