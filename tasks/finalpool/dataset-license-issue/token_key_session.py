from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py

# find theabs path of this file
file_path = os.path.abspath(__file__)

all_token_key_session = Dict(
    github_allowed_repos = "Annoy-DataSync", # only allowed to operate this repo
    github_read_only = "0", # if your task does not require write access to the repos, please set to 1, otherwise set to 0
)