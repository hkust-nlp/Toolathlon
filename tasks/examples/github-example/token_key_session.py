from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py

# find theabs path of this file
file_path = os.path.abspath(__file__)

all_token_key_session = Dict(
    github_allowed_repos = "TestRepo1,TestRepo2", # 这个任务只允许操作上述两个repo
    github_read_only = "1", # if your task does not require write access to the repos, please set to 1, otherwise set to 0
)