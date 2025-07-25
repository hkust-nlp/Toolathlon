import os
import sys

# Set up the environment
os.chdir("/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-huggingface-upload/workspace")

# Try to install huggingface_hub if not available
try:
    from huggingface_hub import HfApi, create_repo, upload_folder
    print("huggingface_hub is available")
except ImportError:
    import subprocess
    print("Installing huggingface_hub...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import HfApi, create_repo, upload_folder
    print("huggingface_hub installed and imported")

# Set up authentication
hf_token = "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"
api = HfApi(token=hf_token)

# Check if we're authenticated
try:
    user_info = api.whoami()
    print(f"Authenticated as: {user_info['name']}")
except Exception as e:
    print(f"Authentication failed: {e}")
    sys.exit(1)

# Repository details
repo_name = "MyAwesomeModel-TestRepo"
repo_id = f"mcptester0606/{repo_name}"

print(f"Creating repository: {repo_id}")