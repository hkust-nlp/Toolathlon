from addict import Dict
import os
all_token_key_session = Dict(
    google_sheets_folder_id = "1q1hoc0BMFnpSiov1pABy3PbstA4nY2fm",
    google_oauth2_credentials_path = "configs/google_credentials.json",
    google_oauth2_token_path = "configs/google_credentials.json", # I just put them all together in the same file

    # k8s
    kubeconfig_path = "deployment/k8s/configs/cluster241-config.yaml",
)