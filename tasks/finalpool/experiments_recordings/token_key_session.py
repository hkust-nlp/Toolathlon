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

    # Google Sheet Folder ID
    google_sheets_folder_id = "1Zy_Hczc1kY6HoaMXW52lJbl9w8ffn31R",

    # wandb
    wandb_api_key = "b3abe195bd69c07bdc47469d3956ac8d0c008714",

    # canvas    
    canvas_api_token = "mcpcanvasadmintoken1",
    # canvas_domain = "localhost:20086",
    
    # woocommerce
    woocommerce_api_key = "ck_woocommerce_token_frances_11wl",
    woocommerce_api_secret = "cs_woocommerce_token_frances_11wl",
    woocommerce_site_url = "http://localhost:10003/store98",
    
    # k8s
    kubeconfig_path = "X",

    # google cloud and big query
    # uncomment to enable the blocking
    google_cloud_allowed_buckets = "gcpbucket0801,gcpbucket0802",
    google_cloud_allowed_bigquery_datasets = "gcpbgdataset0801,gcpbgdataset0802",
    google_cloud_allowed_log_buckets = "gcplogbucket0801,gcplogbucket0802",
    google_cloud_allowed_instances = "gcpinstance0801,gcpinstance0802",


    # snowflake
    snowflake_op_allowed_databases = "SNOWFLAKE_SAMPLE_DATA,TESTDB1,TESTDB2",

    # emails
    emails_config_file = os.path.join(os.path.dirname(file_path), "email_config.json"),

    # notion
    #notion_integration_key = "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",
    notion_allowed_page_ids = allowed_page_ids, # please do not change this, in notion, allowed page ids are generated automatically
)