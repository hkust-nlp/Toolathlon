from addict import Dict
import os
import json
# I am gradually modifying the tokens to the pseudo account in this project

if os.path.exists("./configs/google_credentials.json"):
    google_credentials_filename = "./configs/google_credentials.json"
elif os.path.exists("./configs/credentials.json"):
    google_credentials_filename = "./configs/credentials.json"
else:
    raise ValueError("No google credentials file found")

with open(google_credentials_filename, "r") as f:
    google_credentials = json.load(f)


all_token_key_session = Dict(


    # K8s
    kubeconfig_path = "tmp/k8s_configs/cluster-helios-config.yaml",

)