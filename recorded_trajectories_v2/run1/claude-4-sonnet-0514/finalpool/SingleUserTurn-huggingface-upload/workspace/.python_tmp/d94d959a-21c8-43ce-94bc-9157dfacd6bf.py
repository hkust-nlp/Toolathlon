import os
from huggingface_hub import HfApi, create_repo, upload_folder

# Set up authentication
hf_token = "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"
api = HfApi(token=hf_token)

# Repository details
repo_name = "MyAwesomeModel-TestRepo"
repo_id = f"mcptester0606/{repo_name}"

try:
    # Create the repository
    print("Creating repository...")
    create_repo(
        repo_id=repo_id,
        token=hf_token,
        repo_type="model",
        exist_ok=True,
        private=False
    )
    print(f"Repository {repo_id} created successfully!")

    # Upload the model folder
    print("Uploading model files...")
    model_folder_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-huggingface-upload/workspace/MyAwesomeModel-TestRepo"
    
    upload_folder(
        folder_path=model_folder_path,
        repo_id=repo_id,
        token=hf_token,
        repo_type="model",
        commit_message="Upload MyAwesomeModel checkpoint with evaluation results"
    )
    
    print(f"Model uploaded successfully to https://huggingface.co/{repo_id}")
    
except Exception as e:
    print(f"Error during upload: {e}")
    # Let's check what files we have in the directory
    print("\nFiles in model directory:")
    for root, dirs, files in os.walk(model_folder_path):
        level = root.replace(model_folder_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")