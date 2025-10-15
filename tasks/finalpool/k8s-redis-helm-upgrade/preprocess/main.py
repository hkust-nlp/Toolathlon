import os
import shutil
import asyncio
from utils.general.helper import run_command
from argparse import ArgumentParser

def clear_directory(dir_path):
    """Clear directory contents if it exists"""
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
                continue
    print(f"Successfully cleared directory: {dir_path}")

# abs_file_path = os.path.abspath(__file__)
# file_dir = os.path.dirname(abs_file_path)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Starting the preprocess script for Redis Helm upgrade task...")
    
    source_values_file = os.path.join(args.agent_workspace, "config/redis-values.yaml")

    # Initialize the Kubernetes cluster with Redis Helm deployment
    print("Constructing the Kind cluster with Redis Helm deployment...")

    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts","init_redis_helm.sh")
    asyncio.run(run_command(
        f"bash {script_path} start {source_values_file} {args.agent_workspace}", 
        debug=True, 
        show_output=True
    )) 
    print("Cluster constructed and Redis deployed via Helm")
    
    print("Initialization complete")
    print("Redis has been deployed to shared-services namespace")
    print("Initial version: 19.0.0")
    # print("Custom values are available at ~/config/redis-values.yaml")