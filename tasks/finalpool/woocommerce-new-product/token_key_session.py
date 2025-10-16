from addict import Dict
import os

all_token_key_session = Dict(
    woocommerce_api_key = "ck_woocommerce_token_walkers147a",
    woocommerce_api_secret = "cs_woocommerce_token_walkers147a",
    woocommerce_site_url = "http://localhost:10003/store97",

    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),

)


