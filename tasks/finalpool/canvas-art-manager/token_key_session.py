from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
all_token_key_session = Dict(
    canvas_api_token = "mcpcanvasadmintoken3",
    emails_config_file = os.path.join(os.path.dirname(__file__), "email_config.json"),
)
