from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
import os
all_token_key_session = Dict(
    admin_canvas_api_token = "mcpcanvasadmintoken1",
    canvas_api_token = "canvas_token_TT1021#WQtww",
    emails_config_file = os.path.join(os.path.dirname(__file__), "email_config.json")
)