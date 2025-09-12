from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
all_token_key_session = Dict(
    admin_canvas_api_token = "mcpcanvasadmintoken1",
    canvas_api_token = "canvas_token_TT1021#WQtww",
    canvas_domain = "localhost:20001",
    emails_config_file = "tasks/finalpool/canvas-homework-grader-python/email_config.json"
)