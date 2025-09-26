from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project

# find theabs path of this file
file_path = os.path.abspath(__file__)

emails_config_file = os.path.join(os.path.dirname(file_path), "emails_config.json")

kubeconfig_path = os.path.join(os.path.dirname(file_path), "k8s_configs", "cluster-cleanup-config.yaml")

all_token_key_session = Dict(
    # poste emails
    emails_config_file = emails_config_file,
    # k8s
    kubeconfig_path = kubeconfig_path,
)