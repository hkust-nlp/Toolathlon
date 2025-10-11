import sys
import os
import asyncio
from argparse import ArgumentParser
import sys
import os
from argparse import ArgumentParser
import asyncio
# Add utils to path
sys.path.append(os.path.dirname(__file__))

from utils.general.helper import run_command, print_color
from utils.app_specific.poste.ops import clear_folder
from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

GOOGLESHEET_URLS = [
]

FOLDER_NAME = "quantitative-financial-analysis"
NEEDED_SUBPAGE_NAME = "Quant Research"

async def main1(args):
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

async def main2(args):
    task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
    duplicated_page_id_file = os.path.join(task_root_path, "files", "duplicated_page_id.txt")
    # delete the old duplicated page id file
    if os.path.exists(duplicated_page_id_file):
        os.remove(duplicated_page_id_file)

    command = f"uv run -m utils.app_specific.notion.notion_remove_and_duplicate "
    command += f"--duplicated_page_id_file {duplicated_page_id_file} "
    command += f"--needed_subpage_name \"{NEEDED_SUBPAGE_NAME}\" "
    await run_command(command, debug=True, show_output=True)

    # example we do have a duplicated page id file, so we can use it to get the duplicated page id
    if not os.path.exists(duplicated_page_id_file):
        raise FileNotFoundError(f"Duplicated page id file {duplicated_page_id_file} not found")
    
    with open(duplicated_page_id_file, "r") as f:
        duplicated_page_id = f.read()
    print_color(f"Duplicated page id: {duplicated_page_id}. Process done!","green")

if __name__ == "__main__":
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    asyncio.run(main1(args))
    asyncio.run(main2(args))
