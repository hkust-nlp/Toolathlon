from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project

# find theabs path of this file
file_path = os.path.abspath(__file__)

allowed_page_id_file = os.path.join(os.path.dirname(file_path), "files", "duplicated_page_id.txt")
with open(allowed_page_id_file, "r") as f:
    allowed_page_ids = f.read()

emails_config_file = os.path.join(os.path.dirname(file_path), "emails_config.json")

all_token_key_session = Dict(

    # poste emails
    emails_config_file = emails_config_file,

    # notion
    notion_allowed_page_ids = allowed_page_ids, # please do not change this, in notion, allowed page ids are generated automatically
)