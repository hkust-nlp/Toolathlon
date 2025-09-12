from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),
)