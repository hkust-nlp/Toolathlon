import os
import sys
import shutil
import asyncio
from utils.general.helper import run_command, get_module_path
from argparse import ArgumentParser
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", )
    parser.add_argument("--launch_time", required=False)
    parser.add_argument("--credentials_file", required=False)
    args = parser.parse_args()
    # 初始化 Google Sheets
    folder_id = all_token_key_session.get("google_sheets_folder_id")
    if not folder_id:
        raise ValueError("Google Sheets folder ID is not set.")

    # 如果没有传入credentials_file参数，则从token_key_session中获取
    credentials_file = args.credentials_file
    if not credentials_file:
        credentials_file = all_token_key_session.get("google_oauth2_credentials_path", "configs/google_credentials.json")
    
    print(f"Initializing Google Sheets ...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_google_sheet')} --folder_id {folder_id} --credentials_file {credentials_file}", debug=True,show_output=True))
    print("Google Sheets initialized")

    # 初始化cluster
    print(f"Initializing cluster ...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_cluster')}", debug=True,show_output=True))
    print("Cluster initialized")

    print("Preprogress finish.")
