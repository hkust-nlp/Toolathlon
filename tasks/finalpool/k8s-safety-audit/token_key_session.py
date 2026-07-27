from addict import Dict
import os
from pathlib import Path

file_path = os.path.abspath(__file__)


def get_instance_suffix() -> str:
    try:
        import yaml
    except ImportError:
        return ""
    for root in [Path.cwd(), *Path(__file__).resolve().parents]:
        config_path = root / "configs" / "ports_config.yaml"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return (yaml.safe_load(f) or {}).get("instance_suffix", "")
            except Exception:
                return ""
    return ""


def kubeconfig_filename(cluster_name: str) -> str:
    return f"{cluster_name}{get_instance_suffix()}-config.yaml"

folder_id_file = os.path.join(os.path.dirname(file_path), "files", "folder_id.txt")
with open(folder_id_file, "r") as f:
    folder_id = f.read().strip()

kubeconfig_path = os.path.join(os.path.dirname(file_path), "k8s_configs", kubeconfig_filename("cluster-safety-audit"))

all_token_key_session = Dict(
    google_sheets_folder_id = folder_id,
    # k8s
    kubeconfig_path = kubeconfig_path,
)