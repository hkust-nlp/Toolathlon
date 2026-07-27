from addict import Dict
import os
from pathlib import Path

print("Load token key session")
# I am gradually modifying the tokens to the pseudo account in this project

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

kubeconfig_path = os.path.join(os.path.dirname(file_path), "k8s_configs", kubeconfig_filename("cluster-mysql"))

all_token_key_session = Dict(
    # k8s
    kubeconfig_path = kubeconfig_path,
)