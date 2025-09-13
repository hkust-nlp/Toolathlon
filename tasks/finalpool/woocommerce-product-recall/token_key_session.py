from addict import Dict
import os
import json

if os.path.exists("./configs/google_credentials.json"):
    google_credentials_filename = "./configs/google_credentials.json"
elif os.path.exists("./configs/credentials.json"):
    google_credentials_filename = "./configs/credentials.json"
else:
    raise ValueError("No google credentials file found")

with open(google_credentials_filename, "r") as f:
    google_credentials = json.load(f)
all_token_key_session = Dict(
    # WooCommerce配置
    #### Serper
    serper_api_key = "96b064e2511394e4b7326a678b716eac8c24c662", # TO BR FILLED, you can fill in multiple keys separated by comma

    #### Google
    google_cloud_console_api_key = "AIzaSyDSrjqAk9N9ZBX2T7hH5R7cxhw4MMiTnu8", 
    
    gcp_project_id = "mcp-bench0606", # TO BE FILLED
    gcp_service_account_path = "configs/gcp-service_account.keys.json", # TO BE FILLED

    # google credentials
    google_client_id = google_credentials["client_id"],
    google_client_secret = google_credentials["client_secret"],
    google_refresh_token = google_credentials["refresh_token"],

    google_sheets_folder_id = "", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    google_oauth2_credentials_path = "configs/google_credentials.json", # make sure you have already copied the json file to this path
    google_oauth2_token_path = "configs/google_credentials.json", # make sure you have already copied the json file to this path
    
    woocommerce_api_key = "ck_woocommerce_token_JH0613Kw2AM",
    woocommerce_api_secret = "cs_woocommerce_token_JH0613Kw2AM",
    woocommerce_site_url = "http://localhost:10003/store93",
    
    # 邮件配置 (poste/emails)
    emails_config_file = os.path.join(os.path.dirname(__file__), "email_config.json"),
)