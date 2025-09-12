from addict import Dict
import os

from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    google_oauth2_credentials_path = "configs/credentials.json",
    google_oauth2_token_path = "configs/credentials.json", # I just put them all together in the same file

    woocommerce_api_key = "ck_woocommerce_token_christine1993",
    woocommerce_api_secret = "cs_woocommerce_token_christine1993",
    woocommerce_site_url = "http://localhost:10003/store88",

    gcp_project_id = "mcp-bench0606",
    gcp_service_account_path = "configs/mcp-bench0606-2b68b5487343.json",

    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_bigquery_datasets = "woocommerce_crm",


    # poste emails
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),

)