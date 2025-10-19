import os
import shutil
import tarfile
from pathlib import Path
from argparse import ArgumentParser

def setup_workspace(agent_workspace: str):
    """Set up the workspace and extract PDF files from bills.tar.gz"""
    workspace_dir = Path(agent_workspace)
    bills_dir = workspace_dir / "bills"
    
    # Create the bills directory
    os.makedirs(bills_dir, exist_ok=True)
    
    # Get the path to the archive file - from initial_workspace/bills/bills.tar.gz
    tarfile_path = workspace_dir / "bills" / "bills.tar.gz"
    
    # Extract PDF files to the workspace
    try:
        with tarfile.open(tarfile_path, 'r:gz') as tar:
            # Get all PDF files
            pdf_members = [member for member in tar.getmembers() if member.name.endswith('.pdf')]
            
            if not pdf_members:
                print(f"No PDF files found in the archive: {tarfile_path}")
                return
            
            # Extract PDF files to the bills directory
            for member in pdf_members:
                # Extract to the bills directory
                tar.extract(member, bills_dir)
                # Move file to the root of bills directory (avoid creating subdirectories)
                extracted_path = bills_dir / member.name
                if extracted_path.exists():
                    print(f"Extracted file: {member.name}")
                else:
                    print(f"Failed to extract file: {member.name}")
            
            print(f"Extracted {len(pdf_members)} PDF files to the workspace")
        
        # delete the bills.tar.gz
        os.remove(tarfile_path)
        print(f"Deleted original compressed file: {tarfile_path}")
        
    except Exception as e:
        print(f"Error occurred during extraction: {e}")
        raise

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Agent workspace directory")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    setup_workspace(args.agent_workspace)
    print("Workspace initialization completed!") 