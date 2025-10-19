import os
import json
import sys
import shutil
from argparse import ArgumentParser
from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError
from configs.token_key_session import all_token_key_session

# Define a constant for the repository name to ensure consistency
REPO_NAME = "MyAwesomeModel-TestRepo"

# def local_cleanup(agent_workspace: str):
#     """Clean up local download directories and any temporary files."""
#     print("--- Starting Local Preprocessing Cleanup ---")
    
#     # Common download directory patterns to clean
#     download_dirs_to_clean = [
#         os.path.join(agent_workspace, "downloads"),
#         os.path.join(agent_workspace, "hf_downloads"), 
#         os.path.join(agent_workspace, REPO_NAME),
#         os.path.join(agent_workspace, f"huggingface_{REPO_NAME}"),
#         # Clean any directory that might contain our repo
#         os.path.join(agent_workspace, "MyAwesomeModel-TestRepo")
#     ]
    
#     for download_dir in download_dirs_to_clean:
#         if os.path.exists(download_dir):
#             try:
#                 print(f"Removing existing download directory: {download_dir}")
#                 shutil.rmtree(download_dir)
#                 print(f"Successfully removed: {download_dir}")
#             except Exception as e:
#                 print(f"Warning: Could not remove {download_dir}: {e}")
    
#     # Also clean any temporary files in the workspace
#     temp_patterns = [".tmp", "tmp_", "temp_"]
#     for item in os.listdir(agent_workspace):
#         item_path = os.path.join(agent_workspace, item)
#         if os.path.isdir(item_path) and any(pattern in item.lower() for pattern in temp_patterns):
#             try:
#                 print(f"Removing temporary directory: {item_path}")
#                 shutil.rmtree(item_path)
#                 print(f"Successfully removed: {item_path}")
#             except Exception as e:
#                 print(f"Warning: Could not remove {item_path}: {e}")
    
#     print("--- Local Preprocessing Cleanup Finished ---")

def remote_cleanup(hf_token: str):
    """Connects to the Hub and deletes the target repository if it exists."""
    if not hf_token or "huggingface_token" in hf_token:
        print("Warning: HUGGING_FACE_TOKEN not provided or is a placeholder. Skipping remote cleanup.", file=sys.stderr)
        return

    print("--- Starting Remote Preprocessing Cleanup ---")
    api = HfApi()
    try:
        username = api.whoami(token=hf_token)['name']
        repo_id = f"{username}/{REPO_NAME}"
        
        print(f"Checking for and deleting pre-existing repository: '{repo_id}'...")
        api.delete_repo(repo_id=repo_id, token=hf_token)
        print(f"Successfully deleted pre-existing repository '{repo_id}'.")
        
    except RepositoryNotFoundError:
        # This is the expected case if the environment is already clean.
        print("Repository does not exist. No remote cleanup needed.")
    except HfHubHTTPError as e:
        # This is a real error (e.g., invalid token) that should stop the process.
        print(f"Fatal Error: A Hugging Face API error occurred during cleanup: {e}", file=sys.stderr)
        print("Please check if your HUGGING_FACE_TOKEN is valid and has delete permissions.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal Error: An unexpected error occurred during remote cleanup: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        print("--- Remote Preprocessing Cleanup Finished ---")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Define the source and destination paths
    destination_dir = args.agent_workspace

    # Ensure the destination directory exists
    os.makedirs(destination_dir, exist_ok=True)

    # The token is expected to be in an environment variable
    
    hf_token = all_token_key_session.huggingface_token
    if not hf_token:
        print("Error: HUGGING_FACE_TOKEN environment variable is not set.", file=sys.stderr)
        raise ValueError("HUGGING_FACE_TOKEN is required for remote cleanup.")

    # Step 1: Clean up the local environment
    # local_cleanup(args.agent_workspace)
    
    # Step 2: Clean up the remote environment
    remote_cleanup(hf_token)
    
    print("\nPreprocessing complete. The environment is ready for the agent.")

    with open(os.path.join(args.agent_workspace, "hf_token.txt"), "w") as f:
        f.write(hf_token)