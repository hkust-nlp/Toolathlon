import os
import shutil
import requests
import json
import sys
import asyncio
from utils.general.helper import run_command, get_module_path
from argparse import ArgumentParser
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session

if __name__ == "__main__":
    parser = ArgumentParser(description='Preprocess NHL back-to-back analysis task')
    parser.add_argument("--agent_workspace", required=True, help="Path to agent workspace")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    
    args = parser.parse_args()
    
    # 初始化 Google Sheets
    folder_id = all_token_key_session.get("google_sheets_folder_id", "1TQpPQxIDy78GTFe9fFvVDrqHu-hHzYJX")
    print(f"Initializing Google Sheets ...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_google_sheet')} --folder_id {folder_id} --credentials_file {args.credentials_file}", debug=True,show_output=True))
    print("Google Sheets initialized")
    
    # 使用固定的initial_workspace路径，因为系统只传递agent_workspace
    # initial_workspace = "tasks/gyy710/NHL-B2B-Analysis/initial_workspace"
    # preprocess(initial_workspace, args.agent_workspace)
    
    print("Preprogress finish.")
