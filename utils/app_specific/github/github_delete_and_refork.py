import sys
import os
from argparse import ArgumentParser
# import asyncio
import requests
# Add utils to path
sys.path.append(os.path.dirname(__file__))

from configs.token_key_session import all_token_key_session
# from utils.app_specific.notion_page_duplicator import NotionPageDuplicator
from utils.general.helper import print_color


def main():
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--source_repo_name", required=True, help="Source repo name") # org/repo
    parser.add_argument("--target_repo_name", required=True, help="Target repo name") # org/name, if no org, just under the user
    parser.add_argument("--read_only", action="store_true", help="Read only mode") # if the task is readonly, if so we only need to fork once
    parser.add_argument("--default_branch_only", action="store_true", help="Only delete the default branch")
    args = parser.parse_args()

    github_token = all_token_key_session.github_token
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    source_repo_name = args.source_repo_name
    target_repo_name = args.target_repo_name
    target_repo_org = None

    if "/" in target_repo_name:
        target_repo_org = target_repo_name.split("/")[0]
        target_repo_name = target_repo_name.split("/")[1]

    # if the task is readonly, we just need to check if the target repo exists
    # as globally we only need to fork once

    # first check if the target repo exists
    existed_flag = False
    if requests.get(f"https://api.github.com/repos/{target_repo_name}", headers=headers).status_code == 200:
        print_color(f"Target repo {target_repo_name} already exists","green")
        existed_flag = True
    else:
        print_color(f"Target repo {target_repo_name} does not exist","yellow")

    if args.read_only and existed_flag:
        print_color(f"This is a read only task and target repo {target_repo_name} already exists, skipping...","green")
        return

    # in all other cases: 1) write tasks, or, 2) read tasks but we have not forked yet
    # we need to delete the target repo first if it exists
    # then fork the repo

    if existed_flag:
        print_color(f"Deleting repo {source_repo_name} and reforking to {target_repo_name}","cyan")
        
        # delete the target repo first if it exists
        delete_url = f"https://api.github.com/repos/{target_repo_name}"

        response = requests.delete(delete_url, headers=headers)
        if response.status_code == 204:
            print_color(f"Deleted repo {target_repo_name}","green")
        else:
            print_color(f"Failed to delete repo {target_repo_name}","red")
            raise Exception(f"Failed to delete repo {target_repo_name}")
    
    print_color(f"Forking repo {source_repo_name} to {target_repo_name}","cyan")
    # refork the repo
    fork_url = f"https://api.github.com/repos/{source_repo_name}/forks"
    data = {
        "name": target_repo_name,
        "default_branch_only": args.default_branch_only
    }
    if target_repo_org is not None:
        data["organization"] = target_repo_org
        
    response = requests.post(fork_url, headers=headers, json=data)
    if response.status_code == 202:
        print_color(f"Forked repo {source_repo_name} to {target_repo_name}","green")
    else:
        print_color(f"Failed to fork repo {source_repo_name} to {target_repo_name}","red")
        raise Exception(f"Failed to fork repo {source_repo_name} to {target_repo_name}")
    
    print_color(f"Forked repo {source_repo_name} to {target_repo_name} successfully","green")

if __name__ == "__main__":
    main()