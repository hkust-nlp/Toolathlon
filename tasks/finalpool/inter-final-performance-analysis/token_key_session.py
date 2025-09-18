from addict import Dict
import os
file_path = os.path.abspath(__file__)

folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")
with open(folder_id_file, "r") as f:
    folder_id = f.read().strip()
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # added, use pseudo account!
    google_sheets_folder_id = folder_id,
) 