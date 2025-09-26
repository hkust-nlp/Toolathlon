import sys
import os
import asyncio
from argparse import ArgumentParser

sys.path.append(os.path.dirname(__file__))

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

GOOGLESHEET_URLS = [
    "https://docs.google.com/spreadsheets/d/1Vs0uhbqvUvV9r7jOBoANvD7Vy1AXzkHQMnns2zOL0Ps/edit?usp=sharing"
]

FOLDER_NAME = "llm-training-dataset"

async def main():
    parser = ArgumentParser(description="GoogleSheet example preprocess")
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
    folder_id_file = os.path.join(task_root_path, "files", "folder_id.txt")

    if os.path.exists(folder_id_file):
        os.remove(folder_id_file)

    drive_service, sheets_service = get_google_service()

    folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
    if not folder_id:
        folder_id = create_folder(drive_service, FOLDER_NAME)

    clear_folder(drive_service, folder_id)

    for sheet_url in GOOGLESHEET_URLS:
        copy_sheet_to_folder(drive_service, sheet_url, folder_id)

    with open(folder_id_file, "w") as f:
        f.write(folder_id)

    print(f"Folder ID saved: {folder_id}")

if __name__ == "__main__":
    asyncio.run(main())