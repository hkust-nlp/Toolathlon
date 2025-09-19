from addict import Dict
import os

file_path = os.path.abspath(__file__)

folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")
with open(folder_id_file, "r") as f:
    folder_id = f.read().strip()

allowed_page_id_file = os.path.join(os.path.dirname(file_path), "files", "duplicated_page_id.txt")
with open(allowed_page_id_file, "r") as f:
    allowed_page_ids = f.read()

all_token_key_session = Dict(
    # ggsheet
    google_sheets_folder_id = folder_id,
    # notion
    notion_allowed_page_ids = allowed_page_ids
)