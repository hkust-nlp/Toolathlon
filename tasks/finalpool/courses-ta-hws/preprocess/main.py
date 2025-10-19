from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os
import tarfile
import glob

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Find files.tar.gz in --agent_workspace
    workspace_path = args.agent_workspace
    tar_pattern = os.path.join(workspace_path, "files.tar.gz")
    
    # Find files.tar.gz file
    tar_files = glob.glob(tar_pattern)
    
    if not tar_files:
        print(f"Failed to find files.tar.gz in {workspace_path}")
        exit(1)
    
    tar_file_path = tar_files[0]
    print(f"Found compressed file: {tar_file_path}")
    
    # Extract
    try:
        with tarfile.open(tar_file_path, 'r:gz') as tar:
            print(f"Extracting to: {workspace_path}")
            tar.extractall(path=workspace_path)
            print("Extraction completed")
    except Exception as e:
        print(f"Extraction failed: {e}")
        exit(1)
    
    # Then delete files.tar.gz
    try:
        os.remove(tar_file_path)
        print(f"Deleted original compressed file: {tar_file_path}")
    except Exception as e:
        print(f"Failed to delete compressed file: {e}")
        exit(1)
    
    print("Processing completed")

    
