from addict import Dict
import os
import json

all_token_key_session = Dict(
    woocommerce_api_key = "ck_woocommerce_token_JH0613Kw2AM",
    woocommerce_api_secret = "cs_woocommerce_token_JH0613Kw2AM",
    woocommerce_site_url = "http://localhost:10003/store93",
    
    emails_config_file = os.path.join(os.path.dirname(__file__), "email_config.json"),
)