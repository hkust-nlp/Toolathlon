from addict import Dict
import os

all_token_key_session = Dict(
    woocommerce_api_key = "ck_woocommerce_token_Jcruz821xB00",
    woocommerce_api_secret = "cs_woocommerce_token_Jcruz821xB00",
    woocommerce_site_url = "http://localhost:10003/store87",
    
    emails_config_file = os.path.join(os.path.dirname(__file__),"email_config.json"),
)