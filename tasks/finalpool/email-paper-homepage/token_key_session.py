from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),
    github_allowed_repos = "My-Homepage,enhancing-llms,ipsum-lorem-all-you-need,llm-adaptive-learning,optimizing-llms-contextual-reasoning", 
    github_read_only = "0", # if your task does not require write access to the repos, please set to 1, otherwise set to 0
)