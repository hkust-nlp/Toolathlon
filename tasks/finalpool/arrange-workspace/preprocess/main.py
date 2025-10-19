from argparse import ArgumentParser
import os
import shutil
import tarfile

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Path to the agent workspace. Must be specified explicitly.")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # Ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    dst_tar_path = os.path.join(args.agent_workspace, "initial_workspace.tar.gz")

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
    
    # Remove the original tar.gz file
    try:
        os.remove(dst_tar_path)
        print(f"Removed the original tar file: {dst_tar_path}")
    except Exception as e:
        print(f"Failed to remove tar file: {e}")
    
    print("Preprocessing completed - workspace files are ready.")

if __name__ == "__main__":
    main()
