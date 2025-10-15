import sys
import os
import asyncio
from argparse import ArgumentParser

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.append(project_root)

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

SOURCE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fKZ2b4R5kFgxGFis9UuJV2ANxth0Kdu_ifK8krlui4o/edit?usp=sharing"

FOLDER_NAME = "inter-ucl-final2325"

async def main():
    parser = ArgumentParser(description="Inter Final Performance Analysis preprocess")
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("=" * 60)
    print("Start Google Sheets preprocess - Inter Final Performance Analysis")
    print("=" * 60)

    # Get task root path
    task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create files directory
    files_dir = os.path.join(task_root_path, "files")
    os.makedirs(files_dir, exist_ok=True)
    
    # Folder ID save file path
    folder_id_file = os.path.join(files_dir, "folder_id.txt")

    # If folder_id.txt file exists, delete it
    if os.path.exists(folder_id_file):
        os.remove(folder_id_file)
        print(f"✓ Old folder ID file cleaned")

    try:
        # Get Google service
        print("Authenticating Google service...")
        drive_service, sheets_service = get_google_service()
        print("✓ Google service authentication successful")

        # Find or create target folder
        print(f"Searching for folder: {FOLDER_NAME}")
        folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
        
        if not folder_id:
            print(f"Folder not found, creating: {FOLDER_NAME}")
            folder_id = create_folder(drive_service, FOLDER_NAME)
            print(f"✓ Folder created: {FOLDER_NAME} (ID: {folder_id})")
        else:
            print(f"✓ Existing folder found: {FOLDER_NAME} (ID: {folder_id})")

        # Clean folder contents
        print("Cleaning folder contents...")
        clear_folder(drive_service, folder_id)
        print("✓ Folder cleaned")

        # Copy source Google Sheet to target folder
        print(f"Copying source Google Sheet to folder...")
        print(f"Source Sheet URL: {SOURCE_SHEET_URL}")
        copied_sheet_id = copy_sheet_to_folder(drive_service, SOURCE_SHEET_URL, folder_id)
        print(f"✓ Successfully copied Google Sheet (new ID: {copied_sheet_id})")

        # Save folder ID to file
        with open(folder_id_file, "w") as f:
            f.write(folder_id)
        print(f"✓ Folder ID saved to: {folder_id_file}")

        print("\n" + "=" * 60)
        print("✓ Preprocess complete: environment is ready")
        print(f"✓ Workspace folder ID: {folder_id}")
        print(f"✓ Template copied, can start task")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Preprocess error: {e}")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())