from argparse import ArgumentParser
import os
import shutil
import json
import tarfile
import glob

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Path to the agent workspace (must be specified)")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # Ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")

    # Extract tar.gz file
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"Extracting to: {args.agent_workspace}")
            # Use the filter parameter to avoid deprecation warning in Python 3.14+
            tar.extractall(path=args.agent_workspace, filter='data')
            print("Extraction completed")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    
    # Delete the compressed file
    try:
        os.remove(dst_tar_path)
        print(f"Deleted compressed file: {dst_tar_path}")
    except Exception as e:
        print(f"Failed to delete compressed file: {e}")
    
    print("Preprocessing complete - LaTeX paper files are ready")

if __name__ == "__main__":
    main()

