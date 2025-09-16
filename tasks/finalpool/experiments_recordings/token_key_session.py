from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py

# find theabs path of this file
file_path = os.path.abspath(__file__)

allowed_page_id_file = os.path.join(os.path.dirname(file_path), "files", "duplicated_page_id.txt")
with open(allowed_page_id_file, "r") as f:
    allowed_page_ids = f.read()

all_token_key_session = Dict(
    # notion
    notion_allowed_page_ids = allowed_page_ids, # please do not change this, in notion, allowed page ids are generated automatically
)