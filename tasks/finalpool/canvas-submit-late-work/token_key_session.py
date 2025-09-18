from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project

file_path = os.path.abspath(__file__)



emails_config_file = os.path.join(os.path.dirname(file_path),  "files" ,"poste.json")



all_token_key_session = Dict( 

 # use local deployed ones, or set up your own token to control
    canvas_api_token = "canvas_token_Zedwards5385",
    admin_canvas_token = "mcpcanvasadmintoken2",
    emails_config_file = emails_config_file,
    admin_email_address = "mcpcanvasadmin2@mcp.com",
    admin_email_password = "mcpcanvasadminpass2",

)