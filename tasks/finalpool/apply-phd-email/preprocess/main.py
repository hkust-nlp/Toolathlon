import sys
import os
import tarfile
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # Add task directory to path
from token_key_session import all_token_key_session
from utils.app_specific.poste.email_import_utils import setup_email_environment

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    # First, handle file extraction (if agent_workspace is specified)
    if args.agent_workspace:
        # Ensure agent workspace exists
        os.makedirs(args.agent_workspace, exist_ok=True)
        dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
        
        # Extract files
        try:
            with tarfile.open(dst_tar_path, 'r:gz') as tar:
                print(f"Extracting application files to: {args.agent_workspace}")
                # Use the filter parameter to avoid deprecation warning in Python 3.14+
                tar.extractall(path=args.agent_workspace, filter='data')
                print("Extraction completed")
        except Exception as e:
            print(f"Extraction failed: {e}")
            # Continue execution, as files may already exist or extraction may not be needed
        
        # Remove the tar file
        try:
            os.remove(dst_tar_path)
            print(f"Deleted original tar file: {dst_tar_path}")
        except Exception as e:
            print(f"Failed to delete tar file: {e}")

    print("Preprocessing...")
    print("Using MCP email import mode")

    # Get the path to the task email backup file
    task_backup_file = Path(__file__).parent / ".." / "files" / "emails_backup.json"

    if not task_backup_file.exists():
        print("❌ Task email backup file not found. Please run the conversion script to generate emails_backup.json first.")
        sys.exit(1)

    # Use utility function to set up email environment
    success = setup_email_environment(
        local_token_key_session=all_token_key_session,
        task_backup_file=str(task_backup_file)
    )

    if not success:
        print("\n❌ Failed to set up email environment!")
        sys.exit(1)