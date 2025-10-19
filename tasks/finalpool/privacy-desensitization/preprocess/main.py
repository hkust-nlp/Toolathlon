from argparse import ArgumentParser
import os
import shutil
import json
import tarfile
import glob

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Path to agent workspace, must be specified explicitly")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # Ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
    
    # Extract tar.gz file
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"Extracting to: {args.agent_workspace}")
            tar.extractall(path=args.agent_workspace)
            print("Extraction completed")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    
    # Delete the tar.gz file
    try:
        os.remove(dst_tar_path)
        print(f"Deleted original archive: {dst_tar_path}")
    except Exception as e:
        print(f"Failed to delete archive: {e}")
    
    # Create desensitized_documents directory (for saving desensitized files)
    desen_docs_dir = os.path.join(args.agent_workspace, "desensitized_documents")
    os.makedirs(desen_docs_dir, exist_ok=True)
    print(f"Created desensitized_documents directory: {desen_docs_dir}")
    
    print("Preprocessing completed")

if __name__ == "__main__":
    main() 