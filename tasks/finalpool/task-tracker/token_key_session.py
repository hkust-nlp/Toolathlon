from addict import Dict
import os
import sys
from pathlib import Path

all_token_key_session = Dict(
    #### Github
    github_token = "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",
    github_allowed_repos = "", # Will be set dynamically from task state
    github_read_only = "0",

    #### Notion
    notion_allowed_page_ids="", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
)