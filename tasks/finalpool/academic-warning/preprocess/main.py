from argparse import ArgumentParser
import os
import sys
import subprocess
import json
from pathlib import Path
from google.oauth2 import service_account
from .ggcloud_clean_log import clean_log
from .ggcloud_clean_dataset import clean_dataset
from .ggcloud_upload import upload_csvs_to_bigquery


def get_project_id(credentials_path):
    try:
        with open(credentials_path, 'r') as f:
            data = json.load(f)
            return data.get("project_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--credentials_file", required=False, default="configs/gcp-service_account.keys.json")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Get credentials file path
    credentials_path = Path(args.credentials_file)
    
    # Make sure the path is absolute
    if not credentials_path.is_absolute():
        credentials_path = Path.cwd() / credentials_path
    
    credentials = service_account.Credentials.from_service_account_file(credentials_path)

    project_id = get_project_id(credentials_path)
    print(f"Using project: {project_id}")

    print("=================  clean log =================")
    clean_log(project_id, credentials)

    print("=================  clean dataset =================")
    clean_dataset(project_id, credentials)

    print("======== wait 10s to make sure that the dataset is configured")
    from time import sleep
    sleep(10)

    print("=================  upload files =================")
    upload_csvs_to_bigquery(
        project_id=project_id,
        dataset_id="academic_warning",
        csv_folder=f"{Path(__file__).parent.resolve()}/../files",
        csv_pattern="*.csv",
        credentials=credentials
    )
