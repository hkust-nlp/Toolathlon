from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
all_token_key_session = Dict(
    canvas_admin_api_token = "mcpcanvasadmintoken3", 
    canvas_admin_domain = "localhost:10001",
    canvas_api_token = "canvas_token_brian1990$p1",

    # canvas_domain = "localhost:20001"
)

teacher_email = "bruiz@mcp.com"