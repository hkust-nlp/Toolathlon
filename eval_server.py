#!/usr/bin/env python3
"""
Toolathlon Remote Evaluation Server

This server allows remote clients to submit evaluation tasks.
Only one task can run at a time, with IP rate limiting (3 tasks per 24 hours).
"""

# Version control
SERVER_VERSION = "1.3"
SUPPORTED_CLIENT_VERSIONS = ["1.3"]  # List of supported client versions
SUPPORTED_WS_CLIENT_VERSIONS = ["1.3"]  # List of supported WS client versions
CLIENT_UPDATE_ACTION = (
    "Please update from https://github.com/hkust-nlp/Toolathlon and download "
    "the latest eval client files: eval_client.py and simple_client_ws.py."
)

import asyncio
import os
import sys
import time
import uuid
import json
import tarfile
import io
import hashlib
import tempfile
import shutil
import yaml
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import uvicorn

def log(msg):
    """Log with timestamp (local time + UTC)"""
    local_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    utc_time = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{local_time}][UTC {utc_time}] {msg}", flush=True)

app = FastAPI(
    title="Toolathlon Eval Server",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ===== Global State =====
current_job: Optional[Dict[str, Any]] = None
# New structure: ip -> list of job records
# Each record: {"job_id": str, "submitted_at": str, "completed_at": str or None, "duration_seconds": int or None}
ip_submission_history: Dict[str, list] = defaultdict(list)
ws_proxy_process = None  # Global WebSocket proxy process
ws_proxy_log_file = None  # Global log file handle
transferred_tasks: Dict[str, set] = defaultdict(set)  # job_id -> set of transferred task names

# ===== Configuration =====
TIMEOUT_SECONDS = 240 * 60  # 240 minutes
MAX_SUBMISSIONS_PER_IP = 3  # Max number of requests per IP
RATE_LIMIT_HOURS = 24  # Time window for request count limit
MAX_DURATION_MINUTES = 180  # Max cumulative duration in minutes (-1 for unlimited)
MAX_WORKERS = 10  # Will be updated in main
DUMPS_DIR = "./dumps_public_service"
RATE_LIMIT_DATA_FILE = "./dumps_public_service/ip_rate_limit_data.json"
SERVER_PORT = 8080  # Will be updated in main
WS_PROXY_PORT = 8081  # Will be updated in main

# ===== Request/Response Models =====

class SubmitEvaluationRequest(BaseModel):
    client_version: Optional[str] = None  # Client version for compatibility check (None means old client without version)
    mode: str  # "public" or "private"
    base_url: str
    api_key: Optional[str] = None
    model_name: str
    workers: int = 10
    custom_job_id: Optional[str] = None  # Allow custom job_id
    model_params: Optional[Dict[str, Any]] = None  # User-specified model parameters
    task_list_content: Optional[str] = None  # Task list file content (each line is a task name)
    skip_container_restart: bool = False  # Skip container restart (for debugging/testing only)
    provider: str = "unified"  # Model provider (default: "unified" for backward compatibility with v1.0 clients)
    ws_client_version: Optional[str] = None  # WebSocket client version (required for private mode in v1.3)
    programmatic_tool_calling: Optional[bool] = None  # Per-job PTC toggle (v1.3+); None means use eval-config default
    ptc_timeout_seconds: Optional[int] = None  # Per-job PTC timeout in seconds (v1.3+)

class SubmitEvaluationResponse(BaseModel):
    status: str
    job_id: str
    client_id: Optional[str] = None
    message: str
    warning: Optional[str] = None  # Warning if job_id already exists

# ===== Helper Functions =====

def load_rate_limit_data():
    """Load IP rate limit data from persistent file"""
    global ip_submission_history

    if not Path(RATE_LIMIT_DATA_FILE).exists():
        log(f"No existing rate limit data file found, starting fresh")
        return

    try:
        with open(RATE_LIMIT_DATA_FILE, 'r') as f:
            data = json.load(f)

        # Convert loaded data back to defaultdict
        ip_submission_history = defaultdict(list, data)

        # Count total records
        total_records = sum(len(records) for records in ip_submission_history.values())
        log(f"Loaded rate limit data: {len(ip_submission_history)} IPs, {total_records} total records")

    except Exception as e:
        log(f"Warning: Failed to load rate limit data: {e}")
        ip_submission_history = defaultdict(list)

def save_rate_limit_data():
    """Save IP rate limit data to persistent file"""
    try:
        # Ensure directory exists
        Path(RATE_LIMIT_DATA_FILE).parent.mkdir(parents=True, exist_ok=True)

        # Convert defaultdict to regular dict for JSON serialization
        data_to_save = dict(ip_submission_history)

        with open(RATE_LIMIT_DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)

        log(f"Saved rate limit data: {len(data_to_save)} IPs")

    except Exception as e:
        log(f"Error: Failed to save rate limit data: {e}")

def load_sensitive_values() -> Dict[str, str]:
    """Load sensitive values from token_key_session.py"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'configs'))
        from token_key_session import all_token_key_session

        sensitive_keys = [
            'serper_api_key',
            'google_cloud_console_api_key',
            'gcp_project_id',
            'google_client_id',
            'google_client_secret',
            'google_refresh_token',
            'github_token',
            'huggingface_token',
            'wandb_api_key',
            'notion_integration_key',
            'notion_integration_key_eval',
            'source_notion_page_url',
            'eval_notion_page_url',
            'snowflake_account',
            'snowflake_user',
            'snowflake_password'
        ]

        sensitive_values = {}
        for key in sensitive_keys:
            value = all_token_key_session.get(key)
            if value and isinstance(value, str) and len(value) > 0:
                sensitive_values[key] = value

        return sensitive_values
    except Exception as e:
        log(f"Warning: Failed to load sensitive values: {e}")
        return {}

def load_instance_config() -> Dict[str, str]:
    """Load instance prefix and container runtime from config files"""
    config = {
        'instance_prefix': '',  # Default: no prefix
        'container_runtime': 'docker'  # Default: docker
    }

    # Read instance_prefix from ports_config.yaml
    try:
        ports_config_path = Path(__file__).parent / 'configs' / 'ports_config.yaml'
        if ports_config_path.exists():
            with open(ports_config_path, 'r') as f:
                ports_config = yaml.safe_load(f)
                instance_prefix = ports_config.get('instance_prefix', '')
                if instance_prefix and isinstance(instance_prefix, str):
                    config['instance_prefix'] = instance_prefix
                    log(f"[Server] Loaded instance_prefix from ports_config.yaml: '{instance_prefix}'")
                else:
                    log(f"[Server] Using default instance_prefix (empty)")
    except Exception as e:
        log(f"Warning: Failed to load instance_prefix from ports_config.yaml: {e}")

    # Read container_runtime from global_configs.py
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'configs'))
        from global_configs import global_configs
        runtime = global_configs.get('podman_or_docker', 'docker')
        if runtime in ['docker', 'podman']:
            config['container_runtime'] = runtime
            log(f"[Server] Loaded container_runtime from global_configs.py: {runtime}")
        else:
            log(f"Warning: Invalid container_runtime '{runtime}', using default 'docker'")
    except Exception as e:
        log(f"Warning: Failed to load container_runtime from global_configs.py: {e}")

    return config

def anonymize_content(content: str, sensitive_values: Dict[str, str]) -> str:
    """Anonymize sensitive values in content"""
    if not content or not sensitive_values:
        return content

    anonymized = content
    for key, value in sensitive_values.items():
        if value and len(value) > 1:
            # Replace with first char + "***" + last char
            replacement = f"{value[0]}***{value[-1]}"
            anonymized = anonymized.replace(value, replacement)

    return anonymized

def anonymize_job_id(job_id: Optional[str]) -> Optional[str]:
    """Anonymize job_id by showing only the stable prefix and last two chars."""
    if not job_id or len(job_id) <= 6:
        return job_id
    return f"{job_id[:6]}{'*' * (len(job_id) - 8)}{job_id[-2:]}"

def anonymize_file_content(file_path: Path, sensitive_values: Dict[str, str]) -> Optional[str]:
    """
    Read and anonymize file content.
    Returns anonymized content as string, or None if binary file.
    """
    try:
        # Try to read as text, replacing invalid UTF-8 bytes
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Anonymize
        return anonymize_content(content, sensitive_values)

    except Exception:
        # Read error, return None
        return None

def anonymize_directory(source_dir: Path, temp_dir: Path, sensitive_values: Dict[str, str]):
    """
    Recursively copy directory and anonymize all text files.

    Args:
        source_dir: Source directory to copy from
        temp_dir: Temporary directory to copy to
        sensitive_values: Dictionary of sensitive values to anonymize
    """
    for item in source_dir.iterdir():
        dest_item = temp_dir / item.name

        if item.is_dir():
            # Recursively process subdirectories
            dest_item.mkdir(exist_ok=True)
            anonymize_directory(item, dest_item, sensitive_values)

        elif item.is_file():
            # Try to anonymize text files
            anonymized_content = anonymize_file_content(item, sensitive_values)

            if anonymized_content is not None:
                # Text file - write anonymized content
                with open(dest_item, 'w', encoding='utf-8') as f:
                    f.write(anonymized_content)
            else:
                # Binary file - copy as is
                shutil.copy2(item, dest_item)

def record_job_completion(job_id: str, client_ip: str, start_timestamp: float):
    """Record job completion time and duration in IP submission history"""
    try:
        end_time = datetime.now()
        duration_seconds = int(time.time() - start_timestamp)

        # Find the job record for this IP and update it
        for record in ip_submission_history[client_ip]:
            if record["job_id"] == job_id:
                record["completed_at"] = end_time.isoformat()
                record["duration_seconds"] = duration_seconds
                break

        # Persist the updated data
        save_rate_limit_data()

        log(f"[Server] Recorded job {job_id} completion: duration = {duration_seconds}s ({duration_seconds/60:.1f} min)")

    except Exception as e:
        log(f"[Server] Warning: Failed to record job completion: {e}")

def is_task_finished(status: dict) -> bool:
    """
    Check if a task is finished (including success and failure cases).

    Returns True if:
    - preprocess failed, OR
    - running failed (no evaluation will happen), OR
    - running succeeded AND evaluation completed (true or false)
    """
    preprocess = status.get('preprocess')
    running = status.get('running')
    evaluation = status.get('evaluation')

    # Case 1: preprocess failed -> task finished (no running, no evaluation)
    if preprocess == 'fail':
        return True

    # Case 2: running failed -> task finished (no evaluation will happen)
    if preprocess == 'done' and running == 'fail':
        return True

    # Case 3: running succeeded (done/timeout/max_turn_exceeded) -> check evaluation
    # evaluation must not be None (must be True or False, indicating evaluation completed)
    if preprocess == 'done' and running in ['done', 'timeout', 'max_turn_exceeded']:
        return evaluation is not None

    return False

def check_job_id_exists(job_id: str) -> bool:
    """Check if job_id already exists in dumps directory or is currently running"""
    # Check if currently running
    if current_job and current_job.get("job_id") == job_id:
        return True

    # Check if directory exists in dumps
    job_dir = Path(DUMPS_DIR) / job_id
    return job_dir.exists()

def check_ip_rate_limit(ip: str) -> tuple[bool, str, dict]:
    """
    Check if IP has exceeded rate limit.

    Returns:
        tuple: (allowed: bool, error_message: str, info: dict)
        info contains: {
            "total_duration_seconds": int,
            "remaining_duration_seconds": int,
            "request_count": int,
            "remaining_requests": int,
            "limit_mode": str  # "both", "duration_only", "count_only", "unlimited"
        }
    """
    now = datetime.now()
    cutoff = now - timedelta(hours=RATE_LIMIT_HOURS)

    # Clean old records (older than RATE_LIMIT_HOURS)
    ip_submission_history[ip] = [
        record for record in ip_submission_history[ip]
        if datetime.fromisoformat(record["submitted_at"]) > cutoff
    ]

    # Calculate stats
    completed_jobs = [r for r in ip_submission_history[ip] if r.get("completed_at") is not None]
    total_duration_seconds = sum(r.get("duration_seconds", 0) for r in completed_jobs)
    request_count = len(ip_submission_history[ip])

    # Determine limit mode
    has_duration_limit = MAX_DURATION_MINUTES != -1
    has_count_limit = MAX_SUBMISSIONS_PER_IP != -1

    if not has_duration_limit and not has_count_limit:
        # Both unlimited
        return True, "", {
            "total_duration_seconds": total_duration_seconds,
            "remaining_duration_seconds": -1,
            "request_count": request_count,
            "remaining_requests": -1,
            "limit_mode": "unlimited"
        }

    # Calculate remaining quotas
    max_duration_seconds = MAX_DURATION_MINUTES * 60 if has_duration_limit else -1
    remaining_duration_seconds = max_duration_seconds - total_duration_seconds if has_duration_limit else -1
    remaining_requests = MAX_SUBMISSIONS_PER_IP - request_count if has_count_limit else -1

    info = {
        "total_duration_seconds": total_duration_seconds,
        "remaining_duration_seconds": remaining_duration_seconds,
        "request_count": request_count,
        "remaining_requests": remaining_requests,
        "limit_mode": "both" if (has_duration_limit and has_count_limit) else
                     ("duration_only" if has_duration_limit else "count_only")
    }

    # Apply rate limit logic based on mode
    if has_duration_limit and has_count_limit:
        # Both limits active: duration first, then count
        if total_duration_seconds < max_duration_seconds:
            # Duration not exceeded - allow
            return True, "", info
        else:
            # Duration exceeded - check count limit
            if request_count >= MAX_SUBMISSIONS_PER_IP:
                # Both exceeded
                oldest = ip_submission_history[ip][0]
                retry_after = datetime.fromisoformat(oldest["submitted_at"]) + timedelta(hours=RATE_LIMIT_HOURS)
                error_msg = (
                    f"Rate limit exceeded:\n"
                    f"  • Cumulative duration: {total_duration_seconds/60:.1f} / {MAX_DURATION_MINUTES} minutes (EXCEEDED)\n"
                    f"  • Request count: {request_count} / {MAX_SUBMISSIONS_PER_IP} (EXCEEDED)\n"
                    f"  • Time window: {RATE_LIMIT_HOURS} hours\n"
                    f"  • Retry after: {retry_after.isoformat()}"
                )
                return False, error_msg, info
            else:
                # Duration exceeded but count ok - allow
                return True, "", info

    elif has_duration_limit:
        # Duration limit only
        if total_duration_seconds >= max_duration_seconds:
            # Find when the oldest completed job will expire
            oldest_completed = min(
                (r for r in completed_jobs),
                key=lambda r: r["completed_at"],
                default=None
            )
            retry_after = datetime.fromisoformat(oldest_completed["completed_at"]) + timedelta(hours=RATE_LIMIT_HOURS) if oldest_completed else now
            error_msg = (
                f"Rate limit exceeded:\n"
                f"  • Cumulative duration: {total_duration_seconds/60:.1f} / {MAX_DURATION_MINUTES} minutes (EXCEEDED)\n"
                f"  • Time window: {RATE_LIMIT_HOURS} hours\n"
                f"  • Retry after: {retry_after.isoformat()}"
            )
            return False, error_msg, info

    elif has_count_limit:
        # Count limit only
        if request_count >= MAX_SUBMISSIONS_PER_IP:
            oldest = ip_submission_history[ip][0]
            retry_after = datetime.fromisoformat(oldest["submitted_at"]) + timedelta(hours=RATE_LIMIT_HOURS)
            error_msg = (
                f"Rate limit exceeded:\n"
                f"  • Request count: {request_count} / {MAX_SUBMISSIONS_PER_IP} (EXCEEDED)\n"
                f"  • Time window: {RATE_LIMIT_HOURS} hours\n"
                f"  • Retry after: {retry_after.isoformat()}"
            )
            return False, error_msg, info

    return True, "", info

async def run_command_async(cmd: list, env: dict, log_file: str):
    """Run command asynchronously and capture output to log file"""
    with open(log_file, 'a') as log_f:
        # Create process in new session so we can kill the entire process tree later
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=log_f,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            start_new_session=True  # Creates new process group for easy cleanup
        )
        return process

async def notify_ws_proxy_job_ended(job_id: str, reason: str):
    """Best-effort notification that releases the private-mode WebSocket slot."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://127.0.0.1:{WS_PROXY_PORT}/internal/disconnect_job",
                params={"job_id": job_id, "reason": reason}
            )

        if response.status_code != 200:
            log(f"[Server] Warning: WebSocket proxy rejected cleanup for job {job_id} (HTTP {response.status_code})")
            return

        result = response.json()
        if result.get("disconnected"):
            log(f"[Server] Released WebSocket client for terminal job {job_id} ({reason})")
        elif result.get("reason") not in {"no_client_connected", "different_job_connected"}:
            log(f"[Server] Warning: WebSocket proxy did not release job {job_id}: {result}")
    except Exception as e:
        # Cleanup notification must never change the evaluation's terminal state.
        log(f"[Server] Warning: Could not notify WebSocket proxy that job {job_id} ended: {e}")

# ===== Background Task Executor =====

async def execute_evaluation(job_id: str, mode: str, config: Dict[str, Any]):
    """Execute evaluation task in background"""
    global current_job

    start_time = time.time()
    job_dir = Path(DUMPS_DIR) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    log_file = str(job_dir / "server_stdout.log")
    ws_proxy_process = None

    # Save needed fields to local variables in case current_job becomes None during execution
    client_ip = current_job.get("client_ip") if current_job else "unknown"
    start_timestamp = current_job.get("start_timestamp") if current_job else start_time

    try:
        with open(log_file, 'w') as f:
            f.write(f"=== Toolathlon Evaluation Server Log ===\n")
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Mode: {mode}\n")
            f.write(f"Model: {config['model_name']}\n")
            f.write(f"Workers: {config['workers']}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            if config.get('model_params'):
                f.write(f"Custom model parameters: {json.dumps(config['model_params'], indent=2)}\n")
            if config.get('skip_container_restart'):
                f.write(f"⚠️  WARNING: Container restart skipped (debugging/testing mode)\n")
            if config.get('task_list_content'):
                f.write(f"Custom task list provided\n")
            f.write(f"{'='*50}\n\n")

        # Save model_params to file if provided
        if config.get('model_params'):
            model_params_file = job_dir / "model_params.json"
            with open(model_params_file, 'w') as f:
                json.dump(config['model_params'], f, indent=2)
            log(f"[Server] Saved custom model parameters to: {model_params_file}")

        # Save task_list to file if provided
        task_list_file = None
        if config.get('task_list_content'):
            task_list_file = job_dir / "task_list.txt"
            with open(task_list_file, 'w') as f:
                f.write(config['task_list_content'])
            log(f"[Server] Saved custom task list to: {task_list_file}")

        # Step 1: Deploy containers (skip if requested)
        if config.get('skip_container_restart'):
            with open(log_file, 'a') as f:
                f.write("=== Step 1: Container deployment SKIPPED (user requested) ===\n")
                f.write("⚠️  WARNING: Skipping container restart is recommended ONLY for:\n")
                f.write("   - Debugging purposes\n")
                f.write("   - Testing a small number of tasks\n")
                f.write("   For complete evaluation, it is STRONGLY recommended to restart containers\n")
                f.write("   to ensure a clean environment.\n\n")
                f.flush()
            log(f"[Server] WARNING: Skipping container restart for job {job_id}")
        else:
            with open(log_file, 'a') as f:
                f.write("=== Step 1: Deploying local containers ===\n")
                f.flush()

            deploy_process = await run_command_async(
                ["bash", "global_preparation/deploy_containers.sh", "true"],
                env=os.environ.copy(),
                log_file=log_file
            )

            await deploy_process.wait()

        with open(log_file, 'a') as f:
            f.write("\n=== Step 2: Running parallel tests ===\n")
            f.flush()

        # Step 2: Run tests
        env = os.environ.copy()

        if mode == "public":
            env["TOOLATHLON_OPENAI_BASE_URL"] = config["base_url"]
            env["TOOLATHLON_OPENAI_API_KEY"] = config.get("api_key", "")
        else:  # private
            env["TOOLATHLON_OPENAI_BASE_URL"] = f"http://localhost:{WS_PROXY_PORT}/v1"
            env["TOOLATHLON_OPENAI_API_KEY"] = "dummy"

        # Set model_params file path if provided
        if config.get('model_params'):
            model_params_file = job_dir / "model_params.json"
            env["TOOLATHLON_MODEL_PARAMS_FILE"] = str(model_params_file)

        # Set task_list file path if provided (override the empty default in run_parallel.sh)
        if task_list_file:
            env["TASK_LIST"] = str(task_list_file)
            log(f"[Server] Using custom task list: {task_list_file}")

        # PTC env injection (v1.3+). main.py reads these env vars and they take
        # precedence over both the --programmatic_tool_calling CLI flag and the
        # eval-config JSON value, so per-job overrides win.
        if config.get('programmatic_tool_calling') is not None:
            env["TOOLATHLON_PROGRAMMATIC_TOOL_CALLING"] = "true" if config['programmatic_tool_calling'] else "false"
            log(f"[Server] PTC: programmatic_tool_calling={config['programmatic_tool_calling']}")
        if config.get('ptc_timeout_seconds') is not None:
            env["TOOLATHLON_PTC_TIMEOUT"] = str(config['ptc_timeout_seconds'])
            log(f"[Server] PTC: ptc_timeout_seconds={config['ptc_timeout_seconds']}")

        run_process = await run_command_async(
            [
                "bash", "scripts/run_parallel.sh",
                config["model_name"],
                str(job_dir),
                config["provider"],  # Use provider from config (v1.1+)
                str(config["workers"])
            ],
            env=env,
            log_file=log_file
        )

        if current_job is not None:
            current_job["process"] = run_process

        # Monitor execution with timeout
        while run_process.returncode is None:
            elapsed = time.time() - start_time

            if elapsed > TIMEOUT_SECONDS:
                with open(log_file, 'a') as f:
                    f.write(f"\n\n!!! TIMEOUT: Task exceeded {TIMEOUT_SECONDS//60} minutes !!!\n")

                run_process.kill()
                await run_process.wait()

                if current_job is not None:
                    current_job["status"] = "timeout"
                    current_job["error"] = f"Task exceeded {TIMEOUT_SECONDS//60} minutes"
                log(f"[Server] Job {job_id} timed out after {elapsed//60:.1f} minutes")

                if mode == "private":
                    await notify_ws_proxy_job_ended(job_id, "timeout")

                # Record completion time and duration
                record_job_completion(job_id, client_ip, start_timestamp)

                return

            await asyncio.sleep(5)

        with open(log_file, 'a') as f:
            f.write("\n=== Step 3: Task completed ===\n")
            f.write(f"Finished: {datetime.now().isoformat()}\n")

        # Read results
        eval_stats_file = job_dir / "eval_stats.json"
        if eval_stats_file.exists():
            with open(eval_stats_file, 'r') as f:
                eval_stats = json.load(f)
            if current_job is not None:
                current_job["eval_stats"] = eval_stats
        else:
            if current_job is not None:
                current_job["eval_stats"] = {"error": "eval_stats.json not found"}

        # Read traj_log_all.jsonl
        traj_log_file = job_dir / "traj_log_all.jsonl"
        if traj_log_file.exists():
            with open(traj_log_file, 'r') as f:
                if current_job is not None:
                    current_job["traj_log_all"] = f.read()
        else:
            if current_job is not None:
                current_job["traj_log_all"] = None

        if current_job is not None:
            current_job["status"] = "completed"
        log(f"[Server] Job {job_id} completed successfully")

        if mode == "private":
            await notify_ws_proxy_job_ended(job_id, "completed")

        # Record completion time and duration
        record_job_completion(job_id, client_ip, start_timestamp)

    except Exception as e:
        error_msg = str(e)
        with open(log_file, 'a') as f:
            f.write(f"\n\n!!! ERROR: {error_msg} !!!\n")

        if current_job is not None:
            current_job["status"] = "failed"
            current_job["error"] = error_msg
        log(f"[Server] Job {job_id} failed: {error_msg}")

        if mode == "private":
            await notify_ws_proxy_job_ended(job_id, "failed")

        # Record completion time and duration
        record_job_completion(job_id, client_ip, start_timestamp)

    finally:
        # Keep job info for 60 seconds for client to retrieve
        await asyncio.sleep(60)
        if current_job and current_job.get("job_id") == job_id:
            current_job = None

# ===== API Endpoints =====

@app.get("/")
async def root():
    return {
        "service": "Toolathlon Remote Evaluation Server",
        "version": SERVER_VERSION,
        "status": "running"
    }

@app.get("/check_server_status")
async def check_server_status():
    """Check if server is busy (public endpoint)"""
    if current_job:
        return {
            "busy": True,
            "job_id": anonymize_job_id(current_job.get("job_id")),
            "mode": current_job.get("mode"),
            "model": current_job.get("model_name"),
            "started_at": current_job.get("started_at")
        }
    else:
        return {
            "busy": False,
            "message": "Server is idle and ready to accept tasks"
        }

@app.post("/submit_evaluation")
async def submit_evaluation(request: Request, data: SubmitEvaluationRequest):
    """Submit an evaluation task"""
    global current_job

    client_ip = request.client.host

    # Check if client has version (old clients won't have this field)
    if data.client_version is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Client version missing",
                "message": "Your client is too old and does not report a version number.",
                "server_version": SERVER_VERSION,
                "action": CLIENT_UPDATE_ACTION
            }
        )

    # Check client version compatibility
    if data.client_version not in SUPPORTED_CLIENT_VERSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Client version not supported",
                "message": f"Client version '{data.client_version}' is not compatible with server version '{SERVER_VERSION}'.",
                "supported_versions": SUPPORTED_CLIENT_VERSIONS,
                "action": CLIENT_UPDATE_ACTION
            }
        )

    # Check workers limit
    if data.workers > MAX_WORKERS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Workers limit exceeded",
                "message": f"Requested workers ({data.workers}) exceeds server limit ({MAX_WORKERS}).",
                "max_workers": MAX_WORKERS
            }
        )

    # Check IP rate limit
    allowed, error_msg, limit_info = check_ip_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    # Check if server is busy
    if current_job is not None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Server is busy",
                "message": "Server is currently processing another task. Please try again later.",
                "current_job_started_at": current_job.get("started_at")
            }
        )

    # Validate mode
    if data.mode not in ["public", "private"]:
        raise HTTPException(status_code=400, detail="Mode must be 'public' or 'private'")

    # Validate provider (v1.1+)
    ALLOWED_PROVIDERS = ["unified", "openai_stateful_responses"]
    if data.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid provider",
                "message": f"Provider '{data.provider}' is not supported. Allowed values: {', '.join(ALLOWED_PROVIDERS)}",
                "allowed_providers": ALLOWED_PROVIDERS
            }
        )

    # Validate WS client version for private mode (v1.3)
    if data.mode == "private":
        if data.ws_client_version is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "WebSocket client version missing",
                    "message": "Private mode requires WebSocket client version 1.3. Your client files may be outdated.",
                    "server_version": SERVER_VERSION,
                    "action": CLIENT_UPDATE_ACTION
                }
            )

        if data.ws_client_version not in SUPPORTED_WS_CLIENT_VERSIONS:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "WebSocket client version not supported",
                    "message": f"WebSocket client version '{data.ws_client_version}' is not compatible with server version '{SERVER_VERSION}'.",
                    "your_ws_client_version": data.ws_client_version,
                    "supported_ws_client_versions": SUPPORTED_WS_CLIENT_VERSIONS,
                    "action": CLIENT_UPDATE_ACTION
                }
            )

    # Generate or use custom job_id
    warning_msg = None
    if data.custom_job_id:
        job_id = data.custom_job_id
        # Check if job_id already exists
        if check_job_id_exists(job_id):
            warning_msg = f"Job ID '{job_id}' already exists in the system."
            log(f"[Server] WARNING: Job ID {job_id} already exists, but accepting request (possible resume)")
    else:
        job_id = f"job_{uuid.uuid4().hex[:12]}"

    client_id = f"client_{uuid.uuid4().hex[:8]}" if data.mode == "private" else None

    # Record IP submission with detailed info
    submission_time = datetime.now()
    ip_submission_history[client_ip].append({
        "job_id": job_id,
        "submitted_at": submission_time.isoformat(),
        "completed_at": None,
        "duration_seconds": None
    })

    # Save after adding new submission
    save_rate_limit_data()

    # Initialize job
    current_job = {
        "job_id": job_id,
        "client_id": client_id,
        "client_ip": client_ip,
        "mode": data.mode,
        "model_name": data.model_name,
        "workers": data.workers,
        "status": "running",
        "started_at": submission_time.isoformat(),
        "start_timestamp": submission_time.timestamp()  # For duration calculation
    }

    # Start background task
    config = {
        "base_url": data.base_url,
        "api_key": data.api_key,
        "model_name": data.model_name,
        "workers": data.workers,
        "model_params": data.model_params,
        "task_list_content": data.task_list_content,
        "skip_container_restart": data.skip_container_restart,
        "provider": data.provider,  # Add provider (v1.1+)
        "programmatic_tool_calling": data.programmatic_tool_calling,  # v1.3+
        "ptc_timeout_seconds": data.ptc_timeout_seconds,  # v1.3+
    }

    asyncio.create_task(execute_evaluation(job_id, data.mode, config))

    log(f"[Server] Accepted job {job_id} from {client_ip} (mode: {data.mode}, provider: {data.provider})")
    if data.model_params:
        log(f"[Server] Using custom model parameters: {json.dumps(data.model_params)}")
    if data.task_list_content:
        # Count number of tasks in the list
        task_count = len([line.strip() for line in data.task_list_content.strip().split('\n') if line.strip()])
        log(f"[Server] Using custom task list with {task_count} tasks")
    if data.skip_container_restart:
        log(f"[Server] WARNING: Container restart will be skipped (debugging/testing mode only)")
    if data.programmatic_tool_calling is not None:
        log(f"[Server] PTC override: programmatic_tool_calling={data.programmatic_tool_calling}")
    if data.ptc_timeout_seconds is not None:
        log(f"[Server] PTC override: ptc_timeout_seconds={data.ptc_timeout_seconds}")

    # Prepare rate limit info for response
    rate_limit_info = {
        "limit_mode": limit_info["limit_mode"],
        "usage": {}
    }

    if limit_info["limit_mode"] in ["both", "duration_only", "unlimited"]:
        if limit_info["remaining_duration_seconds"] == -1:
            rate_limit_info["usage"]["duration"] = "unlimited"
        else:
            rate_limit_info["usage"]["duration"] = {
                "used_minutes": round(limit_info["total_duration_seconds"] / 60, 1),
                "remaining_minutes": round(limit_info["remaining_duration_seconds"] / 60, 1),
                "limit_minutes": MAX_DURATION_MINUTES
            }

    if limit_info["limit_mode"] in ["both", "count_only", "unlimited"]:
        if limit_info["remaining_requests"] == -1:
            rate_limit_info["usage"]["requests"] = "unlimited"
        else:
            rate_limit_info["usage"]["requests"] = {
                "used": limit_info["request_count"] + 1,  # +1 for current request
                "remaining": limit_info["remaining_requests"] - 1,  # -1 because we just added one
                "limit": MAX_SUBMISSIONS_PER_IP
            }

    response = {
        "status": "accepted",
        "job_id": job_id,
        "client_id": client_id,
        "message": "Task accepted and started",
        "rate_limit_info": rate_limit_info
    }

    if warning_msg:
        response["warning"] = warning_msg

    return response

@app.get("/poll_job_status")
async def poll_job_status(job_id: str):
    """Poll job status"""
    # Load sensitive values for anonymization
    sensitive_values = load_sensitive_values()

    if not current_job or current_job.get("job_id") != job_id:
        # Check if job exists in dumps (completed job)
        job_dir = Path(DUMPS_DIR) / job_id
        eval_stats_file = job_dir / "eval_stats.json"

        if eval_stats_file.exists():
            # Use errors='replace' to handle non-UTF-8 bytes gracefully
            with open(eval_stats_file, 'r', encoding='utf-8', errors='replace') as f:
                eval_stats_content = f.read()

            # Anonymize eval_stats
            anonymized_eval_stats = anonymize_content(eval_stats_content, sensitive_values)
            eval_stats = json.loads(anonymized_eval_stats)

            # Also read traj_log_all.jsonl if exists
            traj_log_file = job_dir / "traj_log_all.jsonl"
            traj_log_all = None
            if traj_log_file.exists():
                # Use errors='replace' to handle non-UTF-8 bytes gracefully
                with open(traj_log_file, 'r', encoding='utf-8', errors='replace') as f:
                    traj_log_content = f.read()
                # Anonymize traj_log
                traj_log_all = anonymize_content(traj_log_content, sensitive_values)

            return {
                "status": "completed",
                "eval_stats": eval_stats,
                "traj_log_all": traj_log_all
            }
        else:
            return {
                "status": "cancelled",
                "error": "Job not found or has been cleaned up"
            }

    status = current_job.get("status", "running")
    response = {"status": status}

    if status == "completed":
        # Anonymize eval_stats if present
        eval_stats = current_job.get("eval_stats", {})
        eval_stats_str = json.dumps(eval_stats)
        anonymized_eval_stats_str = anonymize_content(eval_stats_str, sensitive_values)
        response["eval_stats"] = json.loads(anonymized_eval_stats_str)

        # Anonymize traj_log_all if present
        traj_log_all = current_job.get("traj_log_all")
        if traj_log_all:
            response["traj_log_all"] = anonymize_content(traj_log_all, sensitive_values)
        else:
            response["traj_log_all"] = None
    elif status in ["failed", "timeout"]:
        response["error"] = current_job.get("error", "Unknown error")

    return response

@app.get("/internal/validate_job")
async def validate_job(job_id: str, request: Request):
    """
    Internal endpoint to validate if a job_id is currently running.
    Only accessible from localhost for security.
    Used by WebSocket proxy to authenticate connections.
    """
    # Security: Only allow localhost
    client_host = request.client.host if request.client else "unknown"
    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(status_code=403, detail="Access denied: localhost only")

    # A retained terminal job is available for result retrieval, but must no
    # longer authenticate or retain a WebSocket client.
    if (
        current_job
        and current_job.get("job_id") == job_id
        and current_job.get("status") == "running"
    ):
        return {
            "valid": True,
            "job_id": job_id,
            "mode": current_job.get("mode"),
            "started_at": current_job.get("started_at")
        }
    else:
        return {
            "valid": False,
            "status": current_job.get("status") if current_job and current_job.get("job_id") == job_id else "not_found",
            "message": "No active job with this ID"
        }

@app.get("/get_server_log")
async def get_server_log(job_id: str, offset: int = 0):
    """Get server execution log with incremental reading and anonymization"""
    log_file = Path(DUMPS_DIR) / job_id / "server_stdout.log"

    if not log_file.exists():
        return {
            "error": "Log file not found",
            "content": "",
            "offset": 0,
            "size": 0,
            "complete": False
        }

    # Load sensitive values for anonymization
    sensitive_values = load_sensitive_values()

    try:
        # Use errors='replace' to handle non-UTF-8 bytes gracefully
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(offset)
            new_content = f.read()
            new_offset = f.tell()

        # Anonymize content
        anonymized_content = anonymize_content(new_content, sensitive_values)

        file_size = log_file.stat().st_size

        # Check if job is complete
        job_complete = False
        if current_job and current_job.get("job_id") == job_id:
            if current_job.get("status") in ["completed", "failed", "timeout", "cancelled"]:
                job_complete = True
        else:
            job_complete = True

        return {
            "content": anonymized_content,
            "offset": new_offset,
            "size": file_size,
            "complete": job_complete
        }
    except Exception as e:
        return {
            "error": str(e),
            "content": "",
            "offset": offset,
            "size": 0,
            "complete": False
        }

@app.post("/cancel_job")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    global current_job

    if not current_job or current_job.get("job_id") != job_id:
        # Check if job exists in dumps (already completed)
        job_dir = Path(DUMPS_DIR) / job_id
        if job_dir.exists():
            # Job exists but is not running - check if it completed
            eval_stats_file = job_dir / "eval_stats.json"
            if eval_stats_file.exists():
                raise HTTPException(
                    status_code=400,
                    detail="Job has already completed. Cannot cancel a completed job."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Job is not running. It may have already finished or been cancelled."
                )
        else:
            raise HTTPException(status_code=404, detail="Job not found")

    # Kill process tree if exists
    if "process" in current_job:
        process = current_job["process"]
        try:
            # Kill the entire process tree using process group
            pid = process.pid
            log(f"[Server] Killing process tree for PID {pid}...")

            import subprocess
            try:
                # Kill process group (more reliable than pkill)
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                log(f"[Server] Killed process group for PID {pid}")
            except ProcessLookupError:
                log(f"[Server] Process {pid} already terminated")
            except Exception as e:
                log(f"[Server] Warning: Failed to kill process group: {e}")
                # Fallback: kill just the main process
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
        except Exception as e:
            log(f"[Server] Warning: Error during process cleanup: {e}")

    # Load instance configuration
    instance_config = load_instance_config()
    instance_prefix = instance_config['instance_prefix']
    container_runtime = instance_config['container_runtime']

    # Stop and remove task containers matching this instance
    import subprocess
    try:
        # Build container name filter based on instance_prefix
        container_name_filter = f"{instance_prefix}toolathlon"

        log(f"[Server] Cleaning up {container_runtime} containers with prefix '{container_name_filter}'...")

        # Get all containers matching the prefix
        result = subprocess.run(
            [container_runtime, 'ps', '-a', '--filter', f'name={container_name_filter}', '--format', '{{.ID}}'],
            capture_output=True,
            text=True,
            check=False
        )
        container_ids = result.stdout.strip().split('\n')
        container_ids = [cid for cid in container_ids if cid]

        if container_ids:
            # Force remove containers immediately
            subprocess.run([container_runtime, 'rm', '-f'] + container_ids, check=False, timeout=10)
            log(f"[Server] Force removed {len(container_ids)} containers with prefix '{container_name_filter}'")
        else:
            log(f"[Server] No containers found with prefix '{container_name_filter}'")
    except Exception as e:
        log(f"[Server] Warning: Failed to clean up {container_runtime} containers: {e}")

    current_job["status"] = "cancelled"

    if current_job.get("mode") == "private":
        await notify_ws_proxy_job_ended(job_id, "cancelled")

    # Record completion time and duration (for cancelled jobs)
    record_job_completion(job_id, current_job["client_ip"], current_job["start_timestamp"])

    # Clean up after a short delay
    await asyncio.sleep(10)
    if current_job and current_job.get("job_id") == job_id:
        current_job = None

    log(f"[Server] Job {job_id} cancelled")

    return {"status": "cancelled", "job_id": job_id}

@app.get("/get_completed_tasks")
async def get_completed_tasks(job_id: str):
    """
    Get list of completed tasks that haven't been transferred yet.

    Returns:
        List of task names that are finished but not yet transferred
    """
    finalpool_dir = Path(DUMPS_DIR) / job_id / "finalpool"

    if not finalpool_dir.exists():
        return {"task_names": []}

    completed_tasks = []

    for task_dir in finalpool_dir.iterdir():
        if not task_dir.is_dir():
            continue

        task_name = task_dir.name

        # Skip already transferred tasks
        if task_name in transferred_tasks[job_id]:
            continue

        # Check if task is finished
        status_file = task_dir / "status.json"
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)

                if is_task_finished(status):
                    completed_tasks.append(task_name)
            except Exception as e:
                log(f"[Server] Error reading status for task {task_name}: {e}")

    return {"task_names": completed_tasks}

@app.get("/get_task_archive")
async def get_task_archive(job_id: str, task_name: str):
    """
    Get a task directory as a tar.gz archive with MD5 verification.
    All text files are anonymized before packaging.

    Returns:
        Streaming response with tar.gz content and MD5 hash in header
    """
    task_dir = Path(DUMPS_DIR) / job_id / "finalpool" / task_name

    if not task_dir.exists():
        raise HTTPException(status_code=404, detail=f"Task {task_name} not found for job {job_id}")

    # Load sensitive values for anonymization
    sensitive_values = load_sensitive_values()

    temp_dir = None
    try:
        # Create temporary directory for anonymized files
        temp_dir = Path(tempfile.mkdtemp(prefix=f"toolathlon_anon_{task_name}_"))
        temp_task_dir = temp_dir / task_name
        temp_task_dir.mkdir(parents=True)

        # Copy and anonymize all files
        for item in task_dir.iterdir():
            # Exclude legacy_results
            if item.name == "legacy_results":
                continue

            dest_item = temp_task_dir / item.name

            if item.is_dir():
                # Recursively process directory
                dest_item.mkdir(exist_ok=True)
                anonymize_directory(item, dest_item, sensitive_values)
            elif item.is_file():
                # Anonymize single file
                anonymized_content = anonymize_file_content(item, sensitive_values)
                if anonymized_content is not None:
                    # Text file
                    with open(dest_item, 'w', encoding='utf-8') as f:
                        f.write(anonymized_content)
                else:
                    # Binary file
                    shutil.copy2(item, dest_item)

        # Create tar.gz from anonymized directory
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            tar.add(temp_task_dir, arcname=task_name, recursive=True)

        tar_bytes = tar_buffer.getvalue()

        # Calculate MD5
        md5_hash = hashlib.md5(tar_bytes).hexdigest()

        # Mark as transferred
        transferred_tasks[job_id].add(task_name)

        log(f"[Server] Sending task archive: {task_name}, size: {len(tar_bytes)} bytes, MD5: {md5_hash}")

        # Return with MD5 in header
        return Response(
            content=tar_bytes,
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename={task_name}.tar.gz",
                "X-Content-MD5": md5_hash
            }
        )

    except Exception as e:
        log(f"[Server] Error creating archive for task {task_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create archive: {str(e)}")
    finally:
        # Clean up temporary directory
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/get_static_files")
async def get_static_files(job_id: str):
    """
    Get all static files (logs, stats, etc.) as a JSON dictionary.
    All text content is anonymized before returning.

    Returns:
        Dictionary with filename -> content mapping
    """
    job_dir = Path(DUMPS_DIR) / job_id

    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Load sensitive values for anonymization
    sensitive_values = load_sensitive_values()

    static_files = [
        "container_all.log",
        "eval_res_all.jsonl",
        "eval_stats.json",
        "run_all.log",
        "traj_log_all.jsonl"
    ]

    # Find execution_report files
    execution_reports = list(job_dir.glob("execution_report_finalpool_*.json"))

    result = {}

    # Read and anonymize static files
    for filename in static_files:
        file_path = job_dir / filename
        if file_path.exists():
            try:
                # Use errors='replace' to handle non-UTF-8 bytes gracefully
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                # Anonymize content
                anonymized_content = anonymize_content(content, sensitive_values)
                result[filename] = anonymized_content

            except Exception as e:
                log(f"[Server] Error reading {filename}: {e}")
                result[filename] = f"ERROR: {str(e)}"
        else:
            result[filename] = None

    # Read and anonymize execution reports
    for report_path in execution_reports:
        try:
            # Use errors='replace' to handle non-UTF-8 bytes gracefully
            with open(report_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Anonymize content
            anonymized_content = anonymize_content(content, sensitive_values)
            result[report_path.name] = anonymized_content

        except Exception as e:
            log(f"[Server] Error reading {report_path.name}: {e}")

    log(f"[Server] Sending static files for job {job_id}, {len(result)} files (anonymized)")

    return result

# ===== Background Tasks =====

async def cleanup_old_files_periodically():
    """
    Background task that runs every 24 hours to clean up old job directories.
    Deletes directories in DUMPS_DIR that haven't been modified in 7 days.
    """
    while True:
        try:
            await asyncio.sleep(24 * 3600)  # Sleep for 24 hours

            log("[Server] Running periodic cleanup of old job directories...")

            dumps_path = Path(DUMPS_DIR)
            if not dumps_path.exists():
                continue

            now = time.time()
            seven_days_ago = now - (7 * 24 * 3600)

            deleted_count = 0
            for item in dumps_path.iterdir():
                # Skip the rate limit data file
                if item.name == "ip_rate_limit_data.json":
                    continue

                # Only process directories (job folders)
                if not item.is_dir():
                    continue

                # Check last modification time
                try:
                    mtime = item.stat().st_mtime
                    if mtime < seven_days_ago:
                        # Directory older than 7 days, delete it
                        shutil.rmtree(item)
                        deleted_count += 1
                        log(f"[Server] Deleted old job directory: {item.name} (last modified: {datetime.fromtimestamp(mtime).isoformat()})")
                except Exception as e:
                    log(f"[Server] Error deleting directory {item.name}: {e}")

            log(f"[Server] Cleanup complete: deleted {deleted_count} old job directories")

        except asyncio.CancelledError:
            log("[Server] Cleanup task cancelled")
            break
        except Exception as e:
            log(f"[Server] Error in cleanup task: {e}")

# ===== Main =====

def cleanup_on_shutdown():
    """Cleanup running jobs and containers on server shutdown"""
    global current_job, ws_proxy_process, ws_proxy_log_file

    print("\n" + "="*60)
    print("Server shutdown requested (Ctrl+C)")
    print("="*60)

    # Clean up WebSocket proxy
    if ws_proxy_process:
        try:
            print(f"Stopping WebSocket proxy (PID: {ws_proxy_process.pid})...")
            ws_proxy_process.kill()
            ws_proxy_process.wait()
            print("  ✓ WebSocket proxy killed")
        except Exception as e:
            print(f"  ✗ Failed to kill WebSocket proxy: {e}")

        if ws_proxy_log_file:
            try:
                ws_proxy_log_file.close()
            except:
                pass

    if current_job:
        job_id = current_job.get("job_id")
        print(f"Cleaning up running job: {job_id}")

        # Kill process tree
        if "process" in current_job:
            process = current_job["process"]
            try:
                pid = process.pid
                print(f"  - Killing process tree (PID: {pid})...")

                import subprocess
                try:
                    # Kill process group
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                    print(f"  ✓ Process tree killed")
                except ProcessLookupError:
                    print(f"  - Process {pid} already terminated")
                except Exception as e:
                    print(f"  ✗ Failed to kill process group: {e}")
                    # Fallback: kill just the main process
                    try:
                        process.kill()
                        print(f"  ✓ Main process killed")
                    except:
                        pass
            except Exception as e:
                print(f"  ✗ Failed to kill process: {e}")
    else:
        print("No running jobs to clean up")

    # Load instance configuration
    instance_config = load_instance_config()
    instance_prefix = instance_config['instance_prefix']
    container_runtime = instance_config['container_runtime']

    # Clean up containers
    import subprocess
    try:
        container_name_filter = f"{instance_prefix}toolathlon"
        print(f"Cleaning up {container_runtime} containers with prefix '{container_name_filter}'...")

        result = subprocess.run(
            [container_runtime, 'ps', '-a', '--filter', f'name={container_name_filter}', '--format', '{{.ID}}'],
            capture_output=True,
            text=True,
            check=False,
            timeout=10
        )
        container_ids = result.stdout.strip().split('\n')
        container_ids = [cid for cid in container_ids if cid]

        if container_ids:
            print(f"  - Force removing {len(container_ids)} containers...")
            # Use container runtime rm -f to force remove immediately without graceful shutdown
            subprocess.run([container_runtime, 'rm', '-f'] + container_ids, check=False, timeout=10)
            print(f"  ✓ Cleaned up {len(container_ids)} containers")
        else:
            print("  - No containers to clean up")
    except Exception as e:
        print(f"  ✗ Warning: Failed to clean up {container_runtime} containers: {e}")

    print("="*60)
    print("Server shutdown complete")
    print("="*60)

if __name__ == "__main__":
    import sys

    server_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    ws_proxy_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8081
    max_submissions = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    max_duration_minutes = int(sys.argv[5]) if len(sys.argv) > 5 else 180

    # Update global variables
    SERVER_PORT = server_port
    WS_PROXY_PORT = ws_proxy_port
    MAX_SUBMISSIONS_PER_IP = max_submissions
    MAX_WORKERS = max_workers
    MAX_DURATION_MINUTES = max_duration_minutes

    # Load persistent rate limit data
    load_rate_limit_data()

    # Format rate limit messages
    if MAX_SUBMISSIONS_PER_IP == -1:
        count_limit_msg = "Unlimited"
    else:
        count_limit_msg = f"{MAX_SUBMISSIONS_PER_IP} per {RATE_LIMIT_HOURS} hours"

    if MAX_DURATION_MINUTES == -1:
        duration_limit_msg = "Unlimited"
    else:
        duration_limit_msg = f"{MAX_DURATION_MINUTES} minutes per {RATE_LIMIT_HOURS} hours"

    # Determine rate limit mode
    has_duration_limit = MAX_DURATION_MINUTES != -1
    has_count_limit = MAX_SUBMISSIONS_PER_IP != -1

    if not has_duration_limit and not has_count_limit:
        limit_mode = "No rate limiting"
    elif has_duration_limit and has_count_limit:
        limit_mode = f"Dual limit (duration: {duration_limit_msg}, count: {count_limit_msg})"
    elif has_duration_limit:
        limit_mode = f"Duration limit only: {duration_limit_msg}"
    else:
        limit_mode = f"Count limit only: {count_limit_msg}"

    print(f"""
{'='*60}
Toolathlon Remote Evaluation Server
{'='*60}
Server Version: {SERVER_VERSION}
Release: Toolathlon-Verified
Client Requirement: Toolathlon eval client {SERVER_VERSION}
Leaderboard: https://toolathlon.xyz/docs/leaderboard
Release Blog: https://toolathlon.xyz/docs/blog/toolathlon-verified
Supported API Client Versions: {', '.join(SUPPORTED_CLIENT_VERSIONS)}
Supported WebSocket Client Versions: {', '.join(SUPPORTED_WS_CLIENT_VERSIONS)}
Server Port: {server_port}
WebSocket Proxy Port: {ws_proxy_port} (for private mode)
Rate limiting: {limit_mode}
Max workers per task: {max_workers}
Timeout: {TIMEOUT_SECONDS//60} minutes
Output directory: {DUMPS_DIR}
{'='*60}
    """)

    # Start WebSocket proxy server
    print(f"Starting WebSocket proxy server on port {ws_proxy_port}...")
    ws_log_path = Path(DUMPS_DIR) / "ws_proxy.log"
    ws_log_path.parent.mkdir(parents=True, exist_ok=True)

    ws_proxy_log_file = open(str(ws_log_path), 'w', buffering=1)

    import subprocess
    ws_proxy_process = subprocess.Popen(
        [sys.executable, "simple_server_ws.py", str(ws_proxy_port), "--eval-port", str(server_port)],
        stdout=ws_proxy_log_file,
        stderr=subprocess.STDOUT
    )

    print(f"✓ WebSocket proxy started (PID: {ws_proxy_process.pid})")
    print(f"  Log: {ws_log_path}")
    print("="*60)

    # Start background cleanup task when FastAPI starts
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(cleanup_old_files_periodically())
        log("[Server] Started background cleanup task (runs every 24 hours)")

    try:
        # Configure uvicorn logging with timestamps
        import logging

        # Custom formatter with timestamps (local + UTC)
        class TimestampFormatter(logging.Formatter):
            def format(self, record):
                local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                utc_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                record.timestamp = f"[{local_time}][UTC {utc_time}]"
                return super().format(record)

        # Configure uvicorn log format
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": TimestampFormatter,
                    "fmt": "%(timestamp)s %(levelname)s:     %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO"},
                "uvicorn.error": {"level": "INFO"},
                "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
            },
        }

        uvicorn.run(app, host="0.0.0.0", port=server_port, log_config=log_config)
    except KeyboardInterrupt:
        cleanup_on_shutdown()
        print("\nExiting...")
