import asyncio
import sys
import os
import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
import tarfile

from utils.app_specific.poste.local_email_manager import LocalEmailManager


if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    

    print("Preprocessing...")
    # 确保agent workspace存在
    os.makedirs(args.agent_workspace, exist_ok=True)
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")

    
    # 解压缩
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"正在解压缩到: {args.agent_workspace}")
            # Use the filter parameter to avoid deprecation warning in Python 3.14+
            tar.extractall(path=args.agent_workspace, filter='data')
            print("解压缩完成")
    except Exception as e:
        print(f"解压缩失败: {e}")
        exit(1)
    
    # 删除压缩文件
    try:
        os.remove(dst_tar_path)
        print(f"已删除原始压缩文件: {dst_tar_path}")
    except Exception as e:
        print(f"删除压缩文件失败: {e}")
    
    print("预处理完成 - LaTeX论文文件已准备就绪")

    receiver_config_file = Path(__file__).parent / ".." / "files" / "receiver_config.json"
    
    receiver_email_manager = LocalEmailManager(str(receiver_config_file), verbose=True)
    receiver_email_manager.clear_all_emails()