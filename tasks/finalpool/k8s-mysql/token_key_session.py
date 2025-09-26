from addict import Dict
import os

print("Load token key session")
# I am gradually modifying the tokens to the pseudo account in this project

file_path = os.path.abspath(__file__)

kubeconfig_path = os.path.join(os.path.dirname(file_path), "k8s_configs", "cluster-mysql-config.yaml")

all_token_key_session = Dict(
    # k8s
    kubeconfig_path = kubeconfig_path,
)