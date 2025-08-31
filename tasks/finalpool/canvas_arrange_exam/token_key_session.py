from addict import Dict
import os
from pathlib import Path

# I am gradually modifying the tokens to the pseudo account in this project
# Get the directory of this script
script_dir = Path(__file__).parent

all_token_key_session = Dict( 

 # use local deployed ones, or set up your own token to control
    canvas_api_token = "canvas_token_ronald_81q2O",
    canvas_domain = "localhost:20001",
    admin_canvas_token = "mcpcanvasadmintoken2",
    emails_config_file = str(script_dir / "files" / "poste.json"),

)