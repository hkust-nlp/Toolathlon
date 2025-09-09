import sys
import os
from argparse import ArgumentParser
import asyncio
# Add utils to path
sys.path.append(os.path.dirname(__file__))

from configs.token_key_session import all_token_key_session
# from utils.app_specific.notion_page_duplicator import NotionPageDuplicator
from utils.general.helper import run_command, print_color, fork_repo


READONLY = False
FORKING_LIST = [
    # source repo, fork_default_branch_only
    ("lockon-n/TestRepo1", True),
    ("lockon-n/TestRepo2", True),
    ("lockon-n/TestRepo3", False),
]

async def main():
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # 用协程并发多个fork_repo
    # 从source_repo自动解析新的target_repo名称
    real_forking_list = []
    for source_repo, fork_default_branch_only in FORKING_LIST:
        target_repo = source_repo.split("/")[1]
        real_forking_list.append((source_repo, target_repo, fork_default_branch_only, READONLY))

    tasks = [fork_repo(source_repo, target_repo, fork_default_branch_only, readonly) for source_repo, target_repo, fork_default_branch_only, readonly in real_forking_list]
    await asyncio.gather(*tasks)

    print_color("Forking all repos successfully!","green")

if __name__ == "__main__":
    asyncio.run(main())




    