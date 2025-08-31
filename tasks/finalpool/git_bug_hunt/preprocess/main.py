import asyncio
import sys
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path

from utils.local_email import LocalEmailManager

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    

    print("Preprocessing...")

    # 接收方邮件配置文件路径（用于评测清理）
    receiver_config_file = Path(__file__).parent / ".." / "files" / "receiver_config.json"
    
    print("清理接收方邮箱...")
    receiver_email_manager = LocalEmailManager(str(receiver_config_file), verbose=True)
    receiver_email_manager.clear_all_emails()

    print("✅ 已完成接收方邮箱清理！")