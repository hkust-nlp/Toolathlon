from pathlib import Path
import argparse
from utils.github_tools.helper_funcs import create_file, update_file, roll_back_commit, delete_folder_contents, get_latest_commit_sha, check_repo_exists, fork_and_rename, create_paper_repo
import json
def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='Initialize a GitHub repository and update the homepage.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--github_token',
        help='GitHub Personal Access Token',
        default="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"
    )

    parser.add_argument(
        '--repo_owner',
        help='GitHub Repository Owner',
        default="mcptest-user"
    )

    parser.add_argument(
        '--repo_name',
        help='GitHub Repository Name',
        default="My-Homepage"
    )

    parser.add_argument(
        '--branch_name',
        help='Branch name to push the file to',
        default="master"
    )
    
    parser.add_argument(
        '--commit_sha',
        help='Commit SHA to roll back to',
        default="a27ca65dbca3b4684e8ed4a85e47436dbde63b9a"
    )
    
    return parser

def create_paper_repositories(args):
    """Create repositories for the four papers with their structures"""
    # Read rollback commit data
    rollback_path = Path(__file__).parent / ".." / "files" / "rollback_commit_sha.json"
    with open(rollback_path, 'r') as f:
        rollback_data = json.load(f)
    
    # Define the four papers with their repository names and rollback keys
    papers = [
        {
            "name": "2024-05-15-enhancing-llms",
            "repo_name": "enhancing-llms",
            "title": "Enhancing Large Language Models with Advanced Fine-Tuning Techniques",
            "rollback_key": "enhancing"
        },
        {
            "name": "2025-06-01-ipsum-lorem-all-you-need", 
            "repo_name": "ipsum-lorem-all-you-need",
            "title": "Ipsum Lorem is All You Need",
            "rollback_key": "ipsum"
        },
        {
            "name": "2025-06-20-llm-adaptive-learning",
            "repo_name": "llm-adaptive-learning", 
            "title": "Adaptive Learning Strategies for Large Language Models in Dynamic Environments",
            "rollback_key": "adaptive"
        },
        {
            "name": "2025-07-01-optimizing-llms-contextual-reasoning",
            "repo_name": "optimizing-llms-contextual-reasoning",
            "title": "Optimizing Large Language Models for Contextual Reasoning in Multi-Task Environments",
            "rollback_key": "optimizing"
        }
    ]
    
    for paper in papers:
        print(f"\n=== Processing repository for {paper['title']} ===")
        
        # Check if repository exists
        repo_full_name = f"{args.repo_owner}/{paper['repo_name']}"
        repo_exists = check_repo_exists(args.github_token, repo_full_name)
        
        # Get rollback commit for this repository
        rollback_commit = rollback_data.get(paper['rollback_key'])
        
        if repo_exists:
            print(f"Repository {repo_full_name} already exists. Rolling back to commit: {rollback_commit}")
            # Roll back to specified commit
            try:
                roll_back_commit(args.github_token, repo_full_name, rollback_commit, "main")
                print(f"✅ Successfully rolled back repository to commit: {rollback_commit}")
            except Exception as e:
                print(f"❌ Error rolling back repository: {e}")
        else:
            print(f"Repository {repo_full_name} does not exist. Creating new repository...")
            
            # Load structure file
            structure_file_path = Path(__file__).parent / ".." / "files" / "structure_files" / f"{paper['name']}.json"
            with open(structure_file_path, 'r', encoding='utf-8') as f:
                file_structure = json.load(f)
            
            # Load README content
            readme_file_path = Path(__file__).parent / ".." / "files" / "readmes" / f"{paper['name']}.md" 
            with open(readme_file_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            try:
                # Create the repository using create_paper_repo
                repo = create_paper_repo(
                    token=args.github_token,
                    repo_name=paper['repo_name'],
                    paper_title=paper['title'],
                    description=f"Code repository for the paper: {paper['title']}",
                    private=False
                )
                
                # Create all files from the structure
                for file_info in file_structure:
                    file_path = file_info['name']
                    file_content = file_info['content']
                    
                    # Skip creating README.md initially since it exists, we'll update it
                    if file_path == "README.md":
                        continue
                        
                    try:
                        repo.create_file(
                            path=file_path,
                            message=f"Add {file_path}",
                            content=file_content
                        )
                        print(f"  Created: {file_path}")
                    except Exception as e:
                        print(f"  Error creating {file_path}: {e}")
                
                # Update README.md with the content from readmes directory
                try:
                    readme_file = repo.get_contents("README.md")
                    repo.update_file(
                        path="README.md",
                        message="Update README.md with detailed content",
                        content=readme_content,
                        sha=readme_file.sha
                    )
                    print(f"  Updated: README.md with detailed content")
                except Exception as e:
                    print(f"  Error updating README.md: {e}")
                    
                print(f"✅ Successfully created repository: {repo.html_url}")
                
            except Exception as e:
                print(f"❌ Error creating repository for {paper['title']}: {e}")

def update_pubs(args):
    files = [
        "2024-05-15-enhancing-llms.md",
        "2025-01-10-ethical-llms.md",
        "2025-06-01-ipsum-lorem-all-you-need.md",
        "2025-06-15-ipsum-lorem-workshop.md",
        "2025-07-01-optimizing-llms-contextual-reasoning.md",
        "2025-06-20-llm-adaptive-learning.md"
    ]
    for file in files:
        file_path = f"_publications/{file}"
        content_path = Path(__file__).parent / ".." / "files" / "pubs" / file
        with open(content_path, 'r') as f:
            content = f.read()
        create_file(args.github_token, f"{args.repo_owner}/{args.repo_name}", file_path, f"Add {file}", content, args.branch_name)

def main(args):
    
    """主函数，执行 GitHub 仓库初始化和文件更新"""
    repo_exists = check_repo_exists(args.github_token, f"{args.repo_owner}/{args.repo_name}")

    # get the rollback commit SHA from the file
    rollback_path = Path(__file__).parent / ".." / "files" / "rollback_commit_sha.json"
    with open(rollback_path, 'r') as f:
        rollback_data = json.load(f)
    rollback_commit_sha = rollback_data.get("homepage", args.commit_sha)

    # check if the repository exists, if not, fork and rename
    if not repo_exists:
        print(f"Repository {args.repo_owner}/{args.repo_name} does not exist. Creating it now...")
        fork_and_rename(args.github_token, "academicpages/academicpages.github.io", f"{args.repo_name}")
        rollback_commit_sha = get_latest_commit_sha(args.github_token, f"{args.repo_owner}/{args.repo_name}", args.branch_name)
        print(f"Repository {args.repo_owner}/{args.repo_name} created successfully. Proceeding with updates.")
    else:
        print(f"Repository {args.repo_owner}/{args.repo_name} already exists. Proceeding with updates.")

    # Roll back the commit to the specified SHA
    roll_back_commit(args.github_token, f"{args.repo_owner}/{args.repo_name}", rollback_commit_sha, args.branch_name)

    # Initialize the repository with the homepage content

    # Update the _config.yml file
    config_path = Path(__file__).parent / ".." / "files" / "_config.yml"
    with open(config_path, 'r') as file:
        config_content = file.read()
    update_file(args.github_token, f"{args.repo_owner}/{args.repo_name}", "_config.yml", "Update _config.yml", config_content, args.branch_name)

    # Update the _includes/archive-single.html
    archive_single_path = Path(__file__).parent / ".." / "files" / "archive-single.html"
    with open(archive_single_path, 'r') as file:
        archive_single_content = file.read()
    update_file(args.github_token, f"{args.repo_owner}/{args.repo_name}", "_includes/archive-single.html", "Update _includes/archive-single.html", archive_single_content, args.branch_name)

    # Update the _layouts/single.html
    single_layout_path = Path(__file__).parent / ".." / "files" / "single.html"
    with open(single_layout_path, 'r') as file:
        single_layout_content = file.read()
    update_file(args.github_token, f"{args.repo_owner}/{args.repo_name}", "_layouts/single.html", "Update _layouts/single.html", single_layout_content, args.branch_name)

    # Delete the contents of the _publications folder and update it with new files
    delete_folder_contents(args.github_token, f"{args.repo_owner}/{args.repo_name}", "_publications", args.branch_name)
    update_pubs(args)
    print(f"Repository {args.repo_owner}/{args.repo_name} has been initialized and updated successfully.")

    # Create/rollback paper repositories
    print("\n=== Processing paper repositories ===")
    create_paper_repositories(args)

    # Save the latest commit SHA to a file
    latest_sha = get_latest_commit_sha(args.github_token, f"{args.repo_owner}/{args.repo_name}", args.branch_name)
    save_path = Path(__file__).parent / ".." / "files" / "init_commit_sha.json"
    with open(save_path, 'w') as f:
        json.dump({"init_commit_sha": latest_sha}, f)

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = create_parser()
    args = parser.parse_args()
    main(args)












#     async def run_mcp_server_command(github_token, payload_data, command_description="", debug=False, show_output=False):
#     print(f"\n--- Running: {command_description} ---")
#     json_payload_bytes = (json.dumps(payload_data) + '\n').encode('utf-8')

#     # Construct the Podman command using a list for better argument handling
#     command = [
#         "podman",
#         "run",
#         "-i",   # Interactive (stdin connected)
#         "--rm", # Remove container after exit
#         "-e",   # Set environment variable
#         f"GITHUB_PERSONAL_ACCESS_TOKEN={github_token}",
#         "ghcr.io/github/github-mcp-server"
#     ]

#     try:
#         # Create subprocess
#         process = await asyncio.create_subprocess_exec(
#             *command, # Unpack the list of command arguments
#             stdin=asyncio.subprocess.PIPE,
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
#         if debug:
#             print(f"Executing command: {' '.join(command)}")

#         # Write payload to stdin and wait for command to complete
#         stdout, stderr = await process.communicate(input=json_payload_bytes)

#         stdout_decoded = stdout.decode('utf-8').strip()
#         stderr_decoded = stderr.decode('utf-8').strip()

#         if show_output and stdout_decoded:
#             print(f"Command output:\n{stdout_decoded}")

#         if process.returncode != 0:
#             print(f"Command failed with exit code: {process.returncode} ❌")
#             if stdout_decoded:
#                 print("Standard Output (stdout - even on error):")
#                 print(stdout_decoded)
#             if stderr_decoded:
#                 print("Standard Error (stderr):")
#                 print(stderr_decoded)
#             return None
#         else:
#             # Attempt to parse the stdout as JSON
#             try:
#                 return json.loads(stdout_decoded)
#             except json.JSONDecodeError:
#                 print("Warning: Could not decode stdout as JSON. 🤔")
#                 if stdout_decoded:
#                     print(f"Raw stdout:\n{stdout_decoded}")
#                 return None

#     except FileNotFoundError:
#         print("Error: 'podman' command not found. ⚠️ Please ensure Podman is installed and in your system's PATH.")
#         return None
#     except Exception as e:
#         print(f"An unexpected error occurred: {e} 🐛")
#         if debug:
#             import traceback
#             traceback.print_exc() # Print full traceback in debug mode
#         return None

# async def create_repo(args):
#     create_repo_payload = {
#         "jsonrpc": "2.0",
#         "id": 3,
#         "method": "tools/call",
#         "params": {
#             "name": "create_repository",
#             "arguments": {
#                 "name": args.repo_name,
#                 "autoInit": True,
#                 "private": False
#             }
#         }
#     }

#     print(f"Attempting to create repository: {args.repo_name}...")
#     # Await the asynchronous command execution
#     create_result = await run_mcp_server_command(args.github_token, create_repo_payload, f"Create Repository '{args.repo_name}'")

#     if create_result and create_result.get("result", {}).get("isError"):
#         error_message = create_result["result"]["content"][0]["text"]
#         if "name already exists on this account" in error_message:
#             print(f"Repository '{args.repo_name}' already exists. Proceeding to push files. 👍")
#             return True # Indicate success for existing repo
#         else:
#             print(f"Failed to create repository with an unexpected error: {error_message}. Aborting. 🛑")
#             return False # Indicate failure
#     elif create_result:
#         print(f"Repository '{args.repo_name}' created successfully! 🎉")
#         return True # Indicate success
#     else:
#         print("Repository creation command failed or returned no result. Aborting. 🛑")
#         return False # Indicate failure

# async def push_file(args):
#     # 2. Read the content of the local HTML file
#     print(f"\nAttempting to read local file: {args.file_to_push}...")
#     try:
#         with open(args.file_to_push, 'r', encoding='utf-8') as f:
#             file_content = f.read()
#         print(f"Successfully read content from {args.file_to_push}.")
#     except FileNotFoundError:
#         print(f"Error: Local file '{args.file_to_push}' not found. Please ensure it's in the same directory as the script. Aborting. 🛑")
#         return False
#     except Exception as e:
#         print(f"Error reading local file '{args.file_to_push}': {e}. Aborting. 🛑")
#         return False

#     # 3. Push the file to the repository
#     push_files_payload = {
#         "jsonrpc": "2.0",
#         "id": 6,
#         "method": "tools/call",
#         "params": {
#             "name": "push_files",
#             "arguments": {
#                 "owner": args.repo_owner,
#                 "repo": args.repo_name,
#                 "branch": args.branch_name,
#                 "message": args.commit_message,
#                 "files": [
#                     {
#                         "path": "my_homepage.html",
#                         "content": file_content
#                     }
#                 ]
#             }
#         }
#     }

#     print(f"\nAttempting to push '{args.file_to_push}' to '{args.repo_owner}/{args.repo_name}' on branch '{args.branch_name}'...")
#     # Await the asynchronous command execution
#     push_result = await run_mcp_server_command(args.github_token, push_files_payload, f"Push file '{args.file_to_push}'")

#     if push_result and not push_result.get("result", {}).get("isError"):
#         print(f"\nSuccessfully pushed '{args.file_to_push}' to '{args.repo_owner}/{args.repo_name}'! 🎉")
#         print(f"You can check your repository at: https://github.com/{args.repo_owner}/{args.repo_name}")
#         return True
#     else:
#         print(f"\nFailed to push '{args.file_to_push}'. See logs above for details. 🛑")
#         return False

# async def init_github_repo(args):
#     # Await the asynchronous functions
#     repo_created = await create_repo(args)
#     if repo_created:
#         await push_file(args)
#     else:
#         print("Repository creation failed, skipping file push. 🚫")

