from addict import Dict
import os

# Token configuration for stock-alert task
all_token_key_session = Dict(
    # WooCommerce credentials
    woocommerce_api_key = "ck_woocommerce_token_benjhMtCdOGk",
    woocommerce_api_secret = "cs_woocommerce_token_benjhMtCdOGk", 
    woocommerce_site_url = "http://localhost:10003/store84",
    woocommerce_admin_username = "mcpwoocommerce",
    woocommerce_admin_password = "mcpwoocommerce",
    
    # Google Sheets credentials
    google_sheets_folder_id = "1A2B3C4D5E6F7G8H9I0J",
    google_oauth2_credentials_path = "configs/google_credentials.json",
    google_oauth2_token_path = "configs/google_auth_state.json",
    
    # Email configuration 
    emails_config_file = "email_config.json",
    
    # GCP configuration
    gcp_project_id = "mcp-bench0606",
    gcp_service_account_path = "configs/gcp-service_account.keys.json",
    
    # API keys
    google_cloud_console_api_key = "AIzaSyD8Q5ZPqCDZIgjOwBc9QtbdFLfGkijBmMU",
)