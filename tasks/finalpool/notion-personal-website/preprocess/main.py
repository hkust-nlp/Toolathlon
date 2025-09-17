import sys
import os
from argparse import ArgumentParser
import asyncio
# Add utils to path
sys.path.append(os.path.dirname(__file__))

from utils.general.helper import run_command, print_color

NEEDED_SUBPAGE_NAME = "Colley Whisson"

async def main():
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

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
    asyncio.run(main())
