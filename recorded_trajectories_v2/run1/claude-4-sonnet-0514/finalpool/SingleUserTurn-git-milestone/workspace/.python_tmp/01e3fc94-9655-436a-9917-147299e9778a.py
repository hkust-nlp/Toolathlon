import json
import os

# Get the current working directory
current_dir = os.getcwd()
print(f"Current directory: {current_dir}")

# Compile the GitHub repository information
github_info = {
    "1": {
        "repo_name": "grit",
        "owner": "mojombo",
        "star_count": 1992,
        "fork_count": 510,
        "creation_time": "2007-10-29T14:37:16Z",
        "description": "**Grit is no longer maintained. Check out libgit2/rugged.** Grit gives you object oriented read/write access to Git repositories via Ruby.",
        "language": "Ruby",
        "repo_url": "https://github.com/mojombo/grit"
    },
    "1000000": {
        "repo_name": "nexus.vim",
        "owner": "vim-scripts",
        "star_count": 2,
        "fork_count": 2,
        "creation_time": "2010-10-18T18:52:14Z",
        "description": "Syntax highlighting for Nexus file format",
        "language": "VimL",
        "repo_url": "https://github.com/vim-scripts/nexus.vim"
    },
    "1000000000": {
        "repo_name": "shit",
        "owner": "Red-Killer",
        "star_count": 3894,
        "fork_count": 280,
        "creation_time": "2025-06-11T05:50:39Z",
        "description": None,
        "language": None,
        "repo_url": "https://github.com/Red-Killer/shit"
    }
}

# Save to JSON file in the current directory
file_path = os.path.join(current_dir, 'github_info.json')
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(github_info, f, indent=2, ensure_ascii=False)

print(f"GitHub milestone repository information has been saved to {file_path}")
print("\nSummary:")
print("- Repository ID 1 (mojombo/grit): ✓ Found - The very first GitHub repository!")
print("- Repository ID 1000: ✗ Not found (likely deleted)")
print("- Repository ID 1000000 (vim-scripts/nexus.vim): ✓ Found - The 1 millionth repository!")
print("- Repository ID 1000000000 (Red-Killer/shit): ✓ Found - The 1 billionth repository!")