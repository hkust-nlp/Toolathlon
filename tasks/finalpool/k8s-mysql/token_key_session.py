from addict import Dict
import os

print("Load token key session")
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # k8s
    kubeconfig_path = "deployment/k8s/configs/cluster-mysql-config.yaml",
)