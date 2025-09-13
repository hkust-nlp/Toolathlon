from addict import Dict
import os

# This token file mirrors the notion-hr style: we don't hardcode a page URL.
# Preprocess will duplicate the template page and write its page_id into files/duplicated_page_id.txt.

file_path = os.path.abspath(__file__)
task_dir = os.path.dirname(file_path)
allowed_page_id_file = os.path.join(task_dir, "files", "duplicated_page_id.txt")

if os.path.exists(allowed_page_id_file):
    with open(allowed_page_id_file, "r") as f:
        allowed_page_ids = f.read()
else:
    allowed_page_ids = ""

all_token_key_session = Dict(
    # Notion: allowed page ids populated by preprocess duplication step
    notion_allowed_page_ids=allowed_page_ids,
)


