#!/usr/bin/env python3
import os
import sys
from argparse import ArgumentParser

FOLDER_NAME = "InvestmentAnalysisWorkspace"

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder
)


def main():
    parser = ArgumentParser(description="Investment Decision Analysis preprocess")
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    try:
        task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
        folder_id_file = os.path.join(task_root_path, "files", "folder_id.txt")

        # Delete old folder_id file
        if os.path.exists(folder_id_file):
            os.remove(folder_id_file)
            print("Old folder_id file deleted")

        # Get Google service
        drive_service, sheets_service = get_google_service()
        print("Google service authentication successful")

        # Find or create folder
        folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
        if not folder_id:
            folder_id = create_folder(drive_service, FOLDER_NAME)
            print(f"Created new folder: {FOLDER_NAME} (ID: {folder_id})")
        else:
            print(f"Found existing folder: {FOLDER_NAME} (ID: {folder_id})")

        # Clean folder content
        clear_folder(drive_service, folder_id)
        print("Folder content cleaned")

        # Save folder_id to file
        with open(folder_id_file, "w") as f:
            f.write(folder_id)

        print(f"Folder ID saved: {folder_id}")
        print("=" * 60)
        print("Preprocessing complete: environment is ready, can start task")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f" Error during preprocessing: {e}")
        print("=" * 60)
        print(" Preprocessing failed: cannot prepare environment")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)