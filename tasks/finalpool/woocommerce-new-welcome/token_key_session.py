from addict import Dict
import os

from addict import Dict
import os

all_token_key_session = Dict(
    woocommerce_api_key = "ck_woocommerce_token_christine1993",
    woocommerce_api_secret = "cs_woocommerce_token_christine1993",
    woocommerce_site_url = "http://localhost:10003/store88",

    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_bigquery_datasets = "woocommerce_crm",

    # poste emails
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),
)