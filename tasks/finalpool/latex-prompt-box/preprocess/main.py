from argparse import ArgumentParser
import os
import shutil
import json
import tarfile
import glob

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Path to the agent workspace. Must be explicitly specified.")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # Ensure the agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    dst_tar_path_paper = os.path.join(args.agent_workspace, "files.tar.gz")
    dsr_tar_path_codes = os.path.join(args.agent_workspace, "codes.tar.gz")

    dst_tar_paths = [dst_tar_path_paper, dsr_tar_path_codes]

    for dst_tar_path in dst_tar_paths:
        # Extract the tar.gz archives
        try:
            with tarfile.open(dst_tar_path, 'r:gz') as tar:
                print(f"Extracting archive to: {args.agent_workspace}")
                # Use the filter parameter to avoid deprecation warning in Python 3.14+
                tar.extractall(path=args.agent_workspace, filter='data')
                print("Extraction completed.")
        except Exception as e:
            print(f"Extraction failed: {e}")
            return
        
        # Delete the original archive file
        try:
            os.remove(dst_tar_path)
            print(f"Original archive deleted: {dst_tar_path}")
        except Exception as e:
            print(f"Failed to delete archive: {e}")
        
    print("Preprocessing complete - LaTeX paper files and code files are ready.")

if __name__ == "__main__":
    main()