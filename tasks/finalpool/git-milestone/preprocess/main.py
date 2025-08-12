#!/usr/bin/env python3
"""
Preprocess script for GitHub milestone repository information collection task.
This script fetches real-time GitHub repository data for specified repo IDs
and stores the results as groundtruth data for evaluation.
"""

import os
import sys
from argparse import ArgumentParser

# Add utils to path
sys.path.append(os.path.dirname(__file__))
from ..utils.github_fetcher import fetch_and_save_github_data


def main():
    """Main function to fetch GitHub repository data."""
    parser = ArgumentParser(description="Fetch real-time GitHub repository data")
    parser.add_argument("--agent_workspace", required=True, 
                       help="Agent workspace path")
    parser.add_argument("--github_token", required=False,
                       help="GitHub personal access token (optional, overrides config token)")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    # Determine the task directory and groundtruth_workspace path
    # This script is in tasks/finalpoolcn/git-milestone/preprocess/main.py
    # We need to find the ../groundtruth_workspace directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    task_dir = os.path.dirname(script_dir)  # Go up from preprocess/ to task root
    groundtruth_workspace = os.path.join(task_dir, "groundtruth_workspace")
    
    # Create output path for before_task.json
    output_path = os.path.join(groundtruth_workspace, "before_task.json")
    
    print("🚀 Starting GitHub repository data collection...")
    print(f"📁 Task directory: {task_dir}")
    print(f"📁 Output path: {output_path}")
    print("🔑 Using GitHub token from config")
    print("-" * 60)
    
    # Fetch and save GitHub data using shared utility
    repo_data = fetch_and_save_github_data(output_path, args.github_token, verbose=True)
    
    if not repo_data:
        print("❌ No repository data was successfully fetched")
        sys.exit(1)
    
    print("-" * 60)
    print("📊 Summary:")
    for repo_id, data in repo_data.items():
        print(f"   Repo {repo_id}: {data['owner']}/{data['repo_name']} "
              f"(⭐{data['star_count']}, 🍴{data['fork_count']})")


if __name__ == "__main__":
    main()