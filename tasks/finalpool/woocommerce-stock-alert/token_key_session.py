from addict import Dict
import os

file_path = os.path.abspath(__file__)
folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")
with open(folder_id_file, "r") as f:
    folder_id = f.read().strip()

# Token configuration for stock-alert task
all_token_key_session = Dict(
    # WooCommerce credentials
    woocommerce_api_key = "ck_woocommerce_token_benjhMtCdOGk",
    woocommerce_api_secret = "cs_woocommerce_token_benjhMtCdOGk", 
    woocommerce_site_url = "http://localhost:10003/store84",

    google_sheets_folder_id = folder_id,
    
    # Email configuration 
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),
)