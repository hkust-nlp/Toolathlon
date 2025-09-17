from argparse import ArgumentParser
from utils.app_specific.github.api import github_get_login, github_delete_repo

from configs.token_key_session import all_token_key_session

GITHUB_TOKEN = all_token_key_session.github_token

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    username = github_get_login(GITHUB_TOKEN)

    github_delete_repo(GITHUB_TOKEN, username, "academicpages.github.io")
    github_delete_repo(GITHUB_TOKEN, username, "LJT-Homepage")

    print("Have deleted the `academicpages.github.io` and `LJT-Homepage` repos for initialization.")
