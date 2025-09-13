from addict import Dict
import os
import json
# I am gradually modifying the tokens to the pseudo account in this project

if os.path.exists("./configs/google_credentials.json"):
    google_credentials_filename = "./configs/google_credentials.json"
elif os.path.exists("./configs/credentials.json"):
    google_credentials_filename = "./configs/credentials.json"
else:
    raise ValueError("No google credentials file found")

with open(google_credentials_filename, "r") as f:
    google_credentials = json.load(f)


all_token_key_session = Dict(
    timezone = "Asia/Hong_Kong",
    ### Remote Ones

    #### Serper
    serper_api_key = "96b064e2511394e4b7326a678b716eac8c24c662", # TO BR FILLED, you can fill in multiple keys separated by comma

    #### Google
    google_cloud_console_api_key = "AIzaSyDSrjqAk9N9ZBX2T7hH5R7cxhw4MMiTnu8", # TO BR FILLED
    
    gcp_project_id = "mcp-bench0606", # TO BE FILLED
    gcp_service_account_path = "configs/gcp-service_account.keys.json", # TO BE FILLED

    # google credentials
    google_client_id = google_credentials["client_id"],
    google_client_secret = google_credentials["client_secret"],
    google_refresh_token = google_credentials["refresh_token"],

    google_sheets_folder_id = "", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    google_oauth2_credentials_path = "configs/google_credentials.json", # make sure you have already copied the json file to this path
    google_oauth2_token_path = "configs/google_credentials.json", # make sure you have already copied the json file to this path
    
    # default set to null to disable the agent from access anything, these will be reset in task specific dir for the names each task needs
    google_cloud_allowed_buckets = "null",
    google_cloud_allowed_bigquery_datasets = "null",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",

    #### Github
    github_token = "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", # TO BR FILLED
    github_allowed_repos = "", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    github_read_only = "1", # default to ban write, but the tasks should open it if needed
    
    #### Huggingface
    huggingface_token = "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", # TO BR FILLED

    #### Wandb
    wandb_api_key = "b3abe195bd69c07bdc47469d3956ac8d0c008714", # TO BR FILLED

    #### Notion
    notion_integration_key="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", # TO BE FILLED
    notion_integration_key_eval = "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", # TO BE FILLED
    source_notion_page_url="https://www.notion.so/Notion-Source-Page-262c4171366e8067863bc8645fd6d51f", # TO BE FILLED
    eval_notion_page_url="https://www.notion.so/Notion-Eval-Page-262c4171366e80a1a366c6f10ee59381", # TO BE FILLED
    notion_allowed_page_ids="", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR


    #### SnowFlake
    snowflake_account = "RXYGDRJ-QA40744", # TO BE FILLED
    snowflake_warehouse = "COMPUTE_WH", # usually `COMPUTE_WH`
    snowflake_role = "ACCOUNTADMIN", # TO BE FILLED
    snowflake_user = "MCPTESTUSER2", # TO BE FILLED
    snowflake_password = "MCPtest0606!!!", # TO BE FILLED
    snowflake_database = "SNOWFLAKE", # we prefill `SNOWFLAKE` here to make compatibility
    snowflake_schema = "PUBLIC", # we prefill `PUBLIC` here to make compatibility
    snowflake_op_allowed_databases = "", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR

    ### Local Ones
    # Canvas, we use the first student's token
    canvas_api_token = "canvas_token_ronald_81q2O", # KEEP_IT_ASIS_CUA_IT_WILL_BE_RESET_IN_TASK_SPECIFIC_DIR
    canvas_domain = "localhost:20001",

    # Woocommerce
    woocommerce_api_key = "ck_woocommerce_token_emma_206rnIn",
    woocommerce_api_secret = "cs_woocommerce_token_emma_206rnIn",
    woocommerce_site_url = "http://localhost:10003/store81",

    # K8s
    kubeconfig_path = "deployment/k8s/configs/cluster1-config.yaml",

    # Poste
    emails_config_file = "configs/example_email_config.json",
)