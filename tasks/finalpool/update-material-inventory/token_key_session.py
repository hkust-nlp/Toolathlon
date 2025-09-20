from addict import Dict
import os

file_path = os.path.abspath(__file__)

folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")
with open(folder_id_file, "r") as f:
    folder_id = f.read().strip()

all_token_key_session = Dict(
    
    woocommerce_api_key = "ck_woocommerce_token_barbg4XESRzo",
    woocommerce_api_secret = "cs_woocommerce_token_barbg4XESRzo",
    woocommerce_site_url = "http://localhost:10003/store91",

    google_sheets_folder_id = folder_id,
)