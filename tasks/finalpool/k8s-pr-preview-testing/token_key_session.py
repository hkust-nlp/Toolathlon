from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # k8s
    kubeconfig_path = "deployment/k8s/configs/cluster-pr-preview-config.yaml",
    github_allowed_repos = "SimpleShopping", # 这个任务只允许操作上述1个repo
    github_read_only = "0", # if your task does not require write access to the repos, please set to 1, otherwise set to 0
)