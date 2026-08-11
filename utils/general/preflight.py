"""Prepare-time preflight checks for tasks with no provisioning step.

These tasks depend on external API keys and third-party remote state that
nothing verifies: a revoked key, exhausted quota, or vanished upstream
resource means prepare "succeeds" and the agent runs against an impossible
task. Each check raises PreflightError on failure; run_preflight runs every
check, reports all results, and exits non-zero if any failed.
"""

import sys

import requests

PLACEHOLDER_VALUES = {"", "XX", "null", "TO BE FILLED"}


class PreflightError(Exception):
    pass


def require_token(name, value):
    """Fail when a token is missing or still the template placeholder."""
    if value is None or str(value).strip() in PLACEHOLDER_VALUES:
        raise PreflightError(f"{name} is not configured (missing or placeholder value)")
    return value


def check_google_maps_key(api_key):
    require_token("google_cloud_console_api_key", api_key)
    resp = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": "1600 Amphitheatre Parkway, Mountain View, CA", "key": api_key},
        timeout=30,
    )
    body = resp.json()
    if body.get("status") != "OK":
        raise PreflightError(
            f"Google Maps geocode probe returned {body.get('status')}: {body.get('error_message', '')}"
        )


def check_youtube_api_key(api_key):
    require_token("google_cloud_console_api_key", api_key)
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "id", "id": "dQw4w9WgXcQ", "key": api_key},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PreflightError(
            f"YouTube Data API probe failed ({resp.status_code}): {resp.text[:300]}"
        )


def check_youtube_playlist(api_key, playlist_id):
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={"part": "id", "playlistId": playlist_id, "maxResults": 1, "key": api_key},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PreflightError(
            f"YouTube playlist {playlist_id} probe failed ({resp.status_code}): {resp.text[:300]}"
        )
    if not resp.json().get("items"):
        raise PreflightError(f"YouTube playlist {playlist_id} exists but has no items")


def check_youtube_channel(api_key, handle):
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "forHandle": handle, "key": api_key},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PreflightError(
            f"YouTube channel {handle} probe failed ({resp.status_code}): {resp.text[:300]}"
        )
    if not resp.json().get("items"):
        raise PreflightError(f"YouTube channel {handle} not found")


def check_wandb_project(api_key, project_path, expected_run_names=()):
    require_token("wandb_api_key", api_key)
    import wandb

    api = wandb.Api(api_key=api_key, timeout=60)
    runs = list(api.runs(project_path))
    if not runs:
        raise PreflightError(f"wandb project {project_path} has no runs")
    if expected_run_names:
        names = {run.name for run in runs}
        missing = [name for name in expected_run_names if name not in names]
        if missing:
            raise PreflightError(
                f"wandb project {project_path} is missing expected runs: {missing}"
            )


def check_hf_token(token):
    require_token("huggingface_token", token)
    resp = requests.get(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PreflightError(
            f"Hugging Face token probe failed ({resp.status_code}): {resp.text[:300]}"
        )


def check_hf_dataset_search(query):
    """The task premise requires at least one Hub dataset matching the query."""
    resp = requests.get(
        "https://huggingface.co/api/datasets",
        params={"search": query, "limit": 5},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PreflightError(
            f"Hugging Face dataset search failed ({resp.status_code}): {resp.text[:300]}"
        )
    if not resp.json():
        raise PreflightError(f"Hugging Face dataset search for '{query}' returned no results")


def check_github_token(token):
    require_token("github_token", token)
    resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PreflightError(
            f"GitHub token probe failed ({resp.status_code}): {resp.text[:300]}"
        )


def check_url_reachable(url, description=None, timeout=20):
    """Reachability only: any response below 500 counts as up."""
    label = description or url
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as e:
        raise PreflightError(f"{label} unreachable: {e}")
    if resp.status_code >= 500:
        raise PreflightError(f"{label} returned {resp.status_code}")


def run_preflight(checks):
    """Run (description, callable) pairs; report all, exit 1 if any failed."""
    failures = []
    for description, check in checks:
        try:
            check()
            print(f"✅ {description}")
        except PreflightError as e:
            print(f"❌ {description}: {e}")
            failures.append(description)
        except Exception as e:
            print(f"❌ {description}: unexpected error: {e}")
            failures.append(description)
    if failures:
        print(f"\nPreflight failed: {', '.join(failures)}")
        sys.exit(1)
    print("\nPreflight passed - required external dependencies are available")
