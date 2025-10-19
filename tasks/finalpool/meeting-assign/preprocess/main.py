from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
from .clean_local_emails import clean_emails
import os
from utils.general.helper import run_command
import asyncio
import tarfile
import shutil

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    try:
        args = parser.parse_args()
    except:
        pass
    
    files_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "files"))
    print(f"files_dir: {files_dir}")
    tmp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
    # first remove tmp_dir
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    # recreate tmp_dir
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"tmp_dir: {tmp_dir}")
    with tarfile.open(os.path.join(files_dir, "files.tar.gz"), "r") as tar:
        tar.extractall(path=tmp_dir)
    print(f"extracted files.tar.gz to {tmp_dir}")

    asyncio.run(run_command(f"kill -9 $(lsof -ti:30137) 2>/dev/null",debug=True,show_output=True))
    asyncio.run(run_command(f"nohup uv run python -m http.server 30137 --directory {tmp_dir} > {tmp_dir}/http.log 2>&1 &",debug=True,show_output=True))

    # clean emails
    receiver_config={
        "email": "jjones@mcp.com",
        "password": "jessica1987%",
        "name": "Meeting Assignment Agent",
        "imap_server": "localhost",
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587,
        "use_ssl": False,
        "use_starttls": False
    }
    clean_emails(receiver_config)
