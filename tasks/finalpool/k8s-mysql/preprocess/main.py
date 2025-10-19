import asyncio
from utils.general.helper import run_command
from argparse import ArgumentParser
from pathlib import Path
import os
import shutil

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Starting the preprocess script, constructing the cluster...")
    script_path = os.path.join(os.path.dirname(__file__), "..","scripts","k8s_mysql.sh")
    asyncio.run(run_command(f"bash {script_path} start {args.agent_workspace}", debug=True,show_output=True))
    print("Cluster constructed")

    # Delete k8s_configs in agent_workspace
    shutil.rmtree(os.path.join(args.agent_workspace, "k8s_configs"))
    print("Deleted local k8s_configs successfully! We will only use the k8s mcp in this task!","green")

    print("Initialization complete")