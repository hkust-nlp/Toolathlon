"""
Generic HuggingFace operations.
"""
from typing import Dict, List, Optional


def hf_get_namespace(token: str) -> str:
    """Get HuggingFace namespace for the authenticated user."""
    try:
        from huggingface_hub import whoami
        hf_info = whoami(token=token)
        return hf_info.get("name") or hf_info.get("orgs")[0]["name"]
    except Exception:
        raise RuntimeError("Failed to determine HuggingFace namespace from token")


def hf_create_dataset(repo_id: str, token: str, private: bool = False) -> None:
    """Create a new HuggingFace dataset repository."""
    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, token=token)


def hf_delete_dataset(repo_id: str, token: str) -> bool:
    """
    Delete a HuggingFace dataset repository.
    Returns True if deleted, False if not found.
    """
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        api.delete_repo(repo_id=repo_id, repo_type="dataset", token=token)
        return True
    except Exception:
        return False


def hf_upload_file(local_file_path: str, repo_id: str, path_in_repo: str, token: str) -> None:
    """Upload a file to a HuggingFace dataset repository."""
    from huggingface_hub import HfApi
    api = HfApi()
    api.upload_file(
        path_or_fileobj=local_file_path,
        path_in_repo=path_in_repo,
        repo_id=repo_id,
        repo_type="dataset",
        token=token,
    )


def hf_delete_datasets_batch(repo_ids: List[str], token: str) -> Dict[str, bool]:
    """
    Delete multiple HuggingFace datasets.
    Returns dict mapping repo_id -> success status.
    """
    results = {}
    for repo_id in repo_ids:
        results[repo_id] = hf_delete_dataset(repo_id, token)
    return results


def extract_hf_dataset_id(hf_url: str) -> Optional[str]:
    """Extract dataset ID from HuggingFace dataset URL."""
    if not hf_url:
        return None
    try:
        from urllib.parse import urlparse
        p = urlparse(hf_url)
        parts = p.path.strip("/").split("/")
        idx = parts.index("datasets")
        ns = parts[idx + 1]
        name = parts[idx + 2]
        return f"{ns}/{name}"
    except Exception:
        return None