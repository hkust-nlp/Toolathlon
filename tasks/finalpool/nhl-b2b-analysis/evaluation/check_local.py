import os
import json
import sys
from pathlib import Path

def check_local(agent_workspace: str, groundtruth_workspace: str) -> tuple[bool, str]:
    """
    Check if CSV files containing keywords are generated in agent workspace
    
    Args:
        agent_workspace: agent workspace path
        groundtruth_workspace: groundtruth workspace path
    
    Returns:
        tuple: (whether check passed, check information)
    """
    
    try:
        workspace_path = Path(agent_workspace)
        
        # Find CSV files containing keywords
        csv_files = list(workspace_path.glob("*.csv"))
        valid_csv_files = []
        
        for csv_file in csv_files:
            # Only check CSV files containing relevant keywords
            name = csv_file.name.lower()
            if any(keyword in name for keyword in ['nhl', 'back', 'b2b', 'back-to-back', 'analysis', 'sheet']):
                valid_csv_files.append(csv_file)
        
        if not valid_csv_files:
            return False, "No CSV files containing NHL back-to-back analysis keywords found"
        
        # Check found CSV files
        csv_details = []
        for csv_file in valid_csv_files:
            try:
                # Simple check if file is readable and non-empty
                with open(csv_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        csv_details.append(f"Found valid CSV file: {csv_file.name}")
                    else:
                        csv_details.append(f"Found empty CSV file: {csv_file.name}")
            except Exception as e:
                csv_details.append(f"CSV file read failed: {csv_file.name} ({e})")
        
        success_msg = f"Local check passed!\nFound CSV files count: {len(valid_csv_files)}\nFile details: {'; '.join(csv_details)}"
        return True, success_msg
        
    except Exception as e:
        return False, f"Local check error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        workspace = sys.argv[1]
        groundtruth = sys.argv[2]
        passed, message = check_local(workspace, groundtruth)
        print(f"Check result: {'Passed' if passed else 'Failed'}")
        print(f"Details: {message}")
    else:
        print("Usage: python check_local.py <agent_workspace> <groundtruth_workspace>")
