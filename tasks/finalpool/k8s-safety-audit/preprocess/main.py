import os
import sys
import shutil
import asyncio
from utils.general.helper import run_command, get_module_path
from argparse import ArgumentParser
from pathlib import Path

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

GOOGLESHEET_URLS = [
    "https://docs.google.com/spreadsheets/d/1Edaz5Aie3HnxrKEaMdjyuFm04O_P8pEx_pp9nm8GCrA/edit?usp=sharing",
]

FOLDER_NAME = "K8sSafetyAudit"

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", )
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    # Part 1 preprocess google sheet
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

    # Part 2 preprocess cluster
    print(f"Initializing cluster ...")
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "k8s_safety_audit.sh")
    asyncio.run(run_command(f"bash {script_path} start {args.agent_workspace}", debug=True,show_output=True))
    print("Cluster initialized")

    # Part 2.5 Delete k8s_configs in agent_workspace
    shutil.rmtree(os.path.join(args.agent_workspace, "k8s_configs"))
    print("Deleted local k8s_configs successfully! We will only use the k8s mcp in this task!")

    print("Preprogress finish.")
