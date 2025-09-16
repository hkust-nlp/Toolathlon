from addict import Dict
import os
from pathlib import Path
import os

all_token_key_session = Dict( 
 # use local deployed ones, or set up your own token to control
    canvas_api_token = "canvas_token_ronald_81q2O",
    admin_canvas_token = "mcpcanvasadmintoken2",
    emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json"),
)