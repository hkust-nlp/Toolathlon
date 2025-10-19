from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    github_allowed_repos = "academicpages.github.io,LJT-Homepage", # Only allowed to operate these 2 repos
    github_read_only = "0", # if your task does not require write access to the repos, please set to 1, otherwise set to 0
)