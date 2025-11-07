from addict import Dict
import os
import json

if os.path.exists("./configs/google_credentials.json"):
    google_credentials_filename = "./configs/google_credentials.json"
elif os.path.exists("./configs/credentials.json"):
    google_credentials_filename = "./configs/credentials.json"
else:
    print("No google credentials file found! This is only expected in quickstart mode!")
    google_credentials_filename = None

if google_credentials_filename is not None:
    with open(google_credentials_filename, "r") as f:
        google_credentials = json.load(f)
else:
    google_credentials = {}


all_token_key_session = Dict(
    timezone = "Asia/Hong_Kong",
    ### Remote Ones

    #### Serper
    serper_api_key = "XX", # TO BE FILLED, you can fill in multiple keys separated by comma

    #### Google
    google_cloud_console_api_key = "XX", # TO BE FILLED
    
    gcp_project_id = "XX", # TO BE FILLED
    gcp_service_account_path = "configs/gcp-service_account.keys.json", # TO BE FILLED

    # google credentials
    google_client_id = google_credentials.get("client_id", ""),
    google_client_secret = google_credentials.get("client_secret", ""),
    google_refresh_token = google_credentials.get("refresh_token", ""),

    google_sheets_folder_id = "XX", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    google_oauth2_credentials_path = "configs/google_credentials.json", # make sure you have already copied the json file to this path
    google_oauth2_token_path = "configs/google_credentials.json", # make sure you have already copied the json file to this path
    
    # default set to null to disable the agent from access anything, these will be reset in task specific dir for the names each task needs
    google_cloud_allowed_buckets = "null",
    google_cloud_allowed_bigquery_datasets = "null",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",

    #### Github
    github_token = "XX", # TO BE FILLED
    github_allowed_repos = "null", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    github_read_only = "1", # default to ban write, but the tasks should open it if needed
    
    #### Huggingface
    huggingface_token = "XX", # TO BE FILLED

    #### Wandb
    wandb_api_key = "XX", # TO BE FILLED

    #### Notion
    notion_integration_key="XX", # TO BE FILLED
    notion_integration_key_eval = "XX", # TO BE FILLED
    source_notion_page_url="XX", # TO BE FILLED
    eval_notion_page_url="XX", # TO BE FILLED
    # notion_allowed_page_ids="XX", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR

    #### SnowFlake
    snowflake_account = "XX", # TO BE FILLED
    snowflake_warehouse = "COMPUTE_WH", # usually `COMPUTE_WH`
    snowflake_role = "ACCOUNTADMIN", # TO BE FILLED
    snowflake_user = "XX", # TO BE FILLED
    snowflake_password = "XX", # TO BE FILLED
    snowflake_database = "SNOWFLAKE", # we prefill `SNOWFLAKE` here to make compatibility
    snowflake_schema = "PUBLIC", # we prefill `PUBLIC` here to make compatibility
    snowflake_op_allowed_databases = "null", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR

    ### Local Ones
    # Canvas, we use the first student's token as an example here
    canvas_api_token = "canvas_token_victoria_14z", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    canvas_domain = "localhost:20001", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR

    # Woocommerce
    # This is also just an example
    woocommerce_api_key = "ck_woocommerce_token_PE0613bf053", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    woocommerce_api_secret = "cs_woocommerce_token_PE0613bf053", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    woocommerce_site_url = "http://localhost:10003/store100", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR

    # K8s
    kubeconfig_path = "deployment/k8s/configs/cluster1-config.yaml", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR

    # Poste
    emails_config_file = "configs/example_email_config.json", # KEEP_IT_ASIS_CUZ_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
)