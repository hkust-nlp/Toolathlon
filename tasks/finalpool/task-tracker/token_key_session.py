from addict import Dict
import os
import sys
from pathlib import Path

file_path = os.path.abspath(__file__)

allowed_page_id_file = os.path.join(os.path.dirname(file_path), "files", "duplicated_page_id.txt")
with open(allowed_page_id_file, "r") as f:
    allowed_page_ids = f.read()

all_token_key_session = Dict(
    #### Github
    github_allowed_repos = "BenchTasksCollv3", # Will be set dynamically from task state
    github_read_only = "0",

    #### Notion
    notion_allowed_page_ids=allowed_page_ids, # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
)