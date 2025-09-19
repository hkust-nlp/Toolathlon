#!/usr/bin/env python3
"""
GDP CR5分析任务预处理脚本
为Agent准备初始工作环境
"""

import os
import shutil
import argparse
import sys
import asyncio
from utils.general.helper import run_command, get_module_path
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session

def main():
    """
    命令行调用的主函数 - 支持系统的参数格式
    """
    parser = argparse.ArgumentParser(description='GDP CR5分析任务预处理')
    parser.add_argument('--agent_workspace', required=True, help='Agent工作区路径')
    parser.add_argument('--launch_time', help='启动时间（可选）')
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    args = parser.parse_args()
    
    # 初始化 Google Sheets
    folder_id = all_token_key_session.get("google_sheets_folder_id", "1Xi5bBHdiyGxYDBud5GqkWYo-DOPkWkZl")
    print(f"Initializing Google Sheets ...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_google_sheet')} --folder_id {folder_id} --credentials_file {args.credentials_file}", debug=True,show_output=True))
    print("Google Sheets initialized")
    
    print("Preprogress finish.")

if __name__ == "__main__":
    main()
