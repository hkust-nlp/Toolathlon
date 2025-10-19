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


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Preprocessing...")
    # Ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")

    # Extract tarball
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"Extracting to: {args.agent_workspace}")
            # Use the filter parameter to avoid deprecation warning in Python 3.14+
            tar.extractall(path=args.agent_workspace, filter='data')
            print("Extraction finished")
    except Exception as e:
        print(f"Failed to extract: {e}")
        exit(1)
    
    # Remove tarball file
    try:
        os.remove(dst_tar_path)
        print(f"Removed original tarball file: {dst_tar_path}")
    except Exception as e:
        print(f"Failed to remove tarball file: {e}")
    
    print("Preprocessing completed - LaTeX paper files are ready")

    receiver_config_file = Path(__file__).parent / ".." / "files" / "receiver_config.json"
    
    receiver_email_manager = LocalEmailManager(str(receiver_config_file), verbose=True)
    receiver_email_manager.clear_all_emails()