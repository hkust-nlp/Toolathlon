import sys
import os
from argparse import ArgumentParser
import asyncio
import shutil
# Add utils to path
sys.path.append(os.path.dirname(__file__))

from configs.token_key_session import all_token_key_session
# from utils.app_specific.notion_page_duplicator import NotionPageDuplicator
from utils.general.helper import run_command, print_color, fork_repo

file_path = os.path.abspath(__file__)
tmp_dir = os.path.join(os.path.dirname(file_path), "..", "tmp")
os.makedirs(tmp_dir, exist_ok=True)

async def main():
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--port", type=int, required=False, help="Port",default=30123)
    args = parser.parse_args()

    # Setup Kubernetes cluster
    print("\nSetting up Kubernetes cluster ...")
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts","k8s_pr_preview_testing.sh")
    await run_command(f"bash {script_path} {args.port} start {args.agent_workspace}", debug=True, show_output=True)

    print_color("Setting up Kubernetes cluster successfully!","green")

    # Delete k8s_configs under agent_workspace
    shutil.rmtree(os.path.join(args.agent_workspace, "k8s_configs"))
    print_color("Deleted local k8s_configs successfully! We will only use the k8s mcp in this task!","green")

if __name__ == "__main__":
    asyncio.run(main())