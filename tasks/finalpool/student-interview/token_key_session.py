from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project

email_config_file = os.path.join(os.path.dirname(__file__), "email_config.json")

all_token_key_session = Dict(
    # poste emails
    emails_config_file = email_config_file,
)