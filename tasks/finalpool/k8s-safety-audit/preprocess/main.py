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
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    args = parser.parse_args()
    # 初始化 Google Sheets
    folder_id = all_token_key_session.get("google_sheets_folder_id", "1q1hoc0BMFnpSiov1pABy3PbstA4nY2fm")
    print(f"Initializing Google Sheets ...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_google_sheet')} --folder_id {folder_id} --credentials_file {args.credentials_file}", debug=True,show_output=True))
    print("Google Sheets initialized")

    # 初始化cluster
    print(f"Initializing cluster ...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_cluster')}", debug=True,show_output=True))
    print("Cluster initialized")

    print("Preprogress finish.")
