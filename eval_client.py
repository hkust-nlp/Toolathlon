#!/usr/bin/env python3
"""
Toolathlon Remote Evaluation Client

Submit evaluation tasks to remote Toolathlon server.
Supports both public API mode and private (local vLLM) mode.
"""

# Version control
CLIENT_VERSION = "1.3"

import asyncio
import json
import os
import sys
import time
import logging
import hashlib
import tarfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


import httpx
import typer

# Import WS client version for private mode validation
try:
    from simple_client_ws import WS_CLIENT_VERSION
except ImportError:
    WS_CLIENT_VERSION = None  # Fallback if file not found

app = typer.Typer(help="Toolathlon Remote Evaluation Client")

# ===== Configuration =====
DEFAULT_SERVER_PORT = 8080
DEFAULT_WS_PROXY_PORT = 8081
TIMEOUT_SECONDS = 240 * 60  # 240 minutes
POLL_INTERVAL_PUBLIC = 10  # seconds
POLL_INTERVAL_PRIVATE = 5  # seconds

# ===== Helper Functions =====

class DownloadRecordManager:
    """Manages download records with MD5 verification"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.record_file = output_dir / ".downloaded_tasks.json"
        self.records = self._load_records()

    def _load_records(self) -> dict:
        """Load download records from file"""
        if self.record_file.exists():
            try:
                with open(self.record_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_records(self):
        """Save download records to file"""
        try:
            with open(self.record_file, 'w') as f:
                json.dump(self.records, f, indent=2)
        except Exception as e:
            log(f"Warning: Failed to save download records: {e}")

    def is_task_complete(self, task_name: str) -> bool:
        """
        Check if a task is completely downloaded.

        Checks:
        1. Record exists with MD5
        2. Task directory exists
        """
        # 1. Check if MD5 record exists
        if task_name not in self.records:
            return False

        # 2. Check if directory exists
        task_dir = self.output_dir / "finalpool" / task_name
        if not task_dir.exists():
            return False

        return True

    def mark_as_complete(self, task_name: str, md5: str):
        """Mark a task as completely downloaded"""
        self.records[task_name] = {
            "md5": md5,
            "downloaded_at": datetime.now().isoformat()
        }
        self._save_records()

    def clear_all(self):
        """Clear all download records (used for --force-redownload)"""
        self.records = {}
        self._save_records()

def ensure_parent_dir(file_path: str):
    """Ensure parent directory exists for a file path"""
    parent = Path(file_path).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

async def cancel_job_on_server(server_url: str, job_id: str, reason: str = "Client error", trust_env: bool = False):
    """Cancel job on server (best effort, don't fail if it doesn't work)"""
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=trust_env) as client:
            await client.post(
                f"{server_url}/cancel_job",
                params={"job_id": job_id}
            )
            log(f"Notified server to cancel job: {reason}")
    except Exception as e:
        log(f"Warning: Failed to notify server about cancellation: {e}")

async def download_task_if_needed(
    task_name: str,
    output_dir: Path,
    server_url: str,
    job_id: str,
    record_manager: DownloadRecordManager,
    force: bool = False,
    trust_env: bool = False
):
    """Download a single task if needed"""
    # Check if already downloaded
    if not force and record_manager.is_task_complete(task_name):
        log(f"[Client] Task {task_name} already complete, skipping")
        return

    if force:
        log(f"[Client] Force redownload: {task_name}")
    else:
        log(f"[Client] Downloading task: {task_name}")

    try:
        # Download task archive
        async with httpx.AsyncClient(timeout=120.0, trust_env=trust_env) as client:
            response = await client.get(
                f"{server_url}/get_task_archive",
                params={"job_id": job_id, "task_name": task_name}
            )

            if response.status_code != 200:
                log(f"[Client] Error downloading {task_name}: HTTP {response.status_code}")
                return

        # Get MD5 from header
        expected_md5 = response.headers.get("X-Content-MD5")
        if not expected_md5:
            log(f"[Client] Warning: No MD5 hash from server for {task_name}")

        # Verify MD5
        tar_bytes = response.content
        calculated_md5 = hashlib.md5(tar_bytes).hexdigest()

        if expected_md5 and calculated_md5 != expected_md5:
            log(f"[Client] MD5 mismatch for {task_name}: expected {expected_md5}, got {calculated_md5}")
            return

        log(f"[Client] MD5 verified: {calculated_md5}")

        # Extract tar.gz (will overwrite existing files)
        finalpool_dir = output_dir / "finalpool"
        finalpool_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r:gz') as tar:
            tar.extractall(finalpool_dir)

        # Mark as complete
        record_manager.mark_as_complete(task_name, calculated_md5)
        log(f"[Client] Task {task_name} downloaded successfully")

    except Exception as e:
        log(f"[Client] Error downloading task {task_name}: {e}")

async def download_static_files(
    output_dir: Path,
    server_url: str,
    job_id: str,
    trust_env: bool = False
):
    """Download all static files from server"""
    log("[Client] Downloading static files...")

    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=trust_env) as client:
            response = await client.get(
                f"{server_url}/get_static_files",
                params={"job_id": job_id}
            )

            if response.status_code != 200:
                log(f"[Client] Error downloading static files: HTTP {response.status_code}")
                return

        files_data = response.json()

        # Save each file
        for filename, content in files_data.items():
            if content is None:
                log(f"[Client] Static file not available: {filename}")
                continue

            file_path = output_dir / filename
            ensure_parent_dir(str(file_path))

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            log(f"[Client] Saved static file: {filename}")

        log("[Client] All static files downloaded successfully")

    except Exception as e:
        log(f"[Client] Error downloading static files: {e}")

# ===== Logging Setup =====

class UTCFormatter(logging.Formatter):
    """Custom formatter that adds both local and UTC timestamps"""
    def format(self, record):
        # Get local time
        local_time = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        # Get UTC time
        utc_time = datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        # Add both to the record
        record.local_time = local_time
        record.utc_time = utc_time
        return super().format(record)

def setup_logging(log_file: str):
    """Setup logging to file only (background worker should not output to terminal)"""
    ensure_parent_dir(log_file)

    # Create file handler with write mode to clear previous logs
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    formatter = UTCFormatter('[%(local_time)s][UTC %(utc_time)s] %(message)s')
    file_handler.setFormatter(formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

def log(message: str):
    """Log a message and flush immediately"""
    logging.info(message)
    # Force flush all handlers to ensure real-time writing
    for handler in logging.getLogger().handlers:
        handler.flush()

def anonymize_job_id(job_id: str) -> str:
    """Anonymize job_id by showing only first 2 and last 2 characters"""
    if not job_id or len(job_id) <= 6:
        return job_id
    return f"{job_id[:6]}{'*' * (len(job_id) - 8)}{job_id[-2:]}"

# ===== Worker Functions =====

async def public_worker(
    server_url: str,
    job_id: str,
    output_dir: str,
    force_redownload: bool,
    trust_env: bool = False
):
    """
    Background worker for public mode
    Only polls status, no LLM request handling needed
    """
    # Derive all file paths from output_dir
    output_dir_path = Path(output_dir)
    log_file = str(output_dir_path / "client.log")
    server_log_file = str(output_dir_path / "server.log")

    setup_logging(log_file)

    log("="*60)
    log("Toolathlon Eval Client - Public Mode Worker")
    log(f"Job ID: {job_id}")
    log(f"Server: {server_url}")
    log(f"Output directory: {output_dir}")
    if force_redownload:
        log("Force redownload: ENABLED")
    log("="*60)

    # Initialize download record manager
    record_manager = DownloadRecordManager(output_dir_path)
    if force_redownload:
        log("Clearing download records for force redownload")
        record_manager.clear_all()

    # Setup signal handlers for graceful shutdown
    import signal

    def signal_handler(signum, frame):
        log(f"\n!!! Received signal {signum}, shutting down...")
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        start_time = time.time()
        server_log_offset = 0

        async with httpx.AsyncClient(timeout=30.0, trust_env=trust_env) as client:
            while True:
                elapsed = time.time() - start_time

                # Check timeout
                if elapsed > TIMEOUT_SECONDS:
                    log(f"ERROR: Task exceeded {TIMEOUT_SECONDS//60} minutes timeout")
                    await cancel_job_on_server(server_url, job_id, "Timeout", trust_env)
                    sys.exit(1)

                # Pull server log
                try:
                    resp = await client.get(
                        f"{server_url}/get_server_log",
                        params={"job_id": job_id, "offset": server_log_offset}
                    )
                    log_data = resp.json()

                    if log_data.get("content"):
                        with open(server_log_file, 'a') as f:
                            f.write(log_data["content"])
                        server_log_offset = log_data["offset"]

                except Exception as e:
                    log(f"Warning: Failed to fetch server log: {e}")

                # Download completed tasks incrementally
                try:
                    resp = await client.get(
                        f"{server_url}/get_completed_tasks",
                        params={"job_id": job_id}
                    )
                    completed_data = resp.json()
                    task_names = completed_data.get("task_names", [])

                    if task_names:
                        log(f"Found {len(task_names)} newly completed tasks")
                        for task_name in task_names:
                            await download_task_if_needed(
                                task_name, output_dir_path, server_url, job_id,
                                record_manager, force_redownload, trust_env
                            )
                except Exception as e:
                    log(f"Warning: Failed to check/download completed tasks: {e}")

                # Poll job status
                try:
                    resp = await client.get(
                        f"{server_url}/poll_job_status",
                        params={"job_id": job_id}
                    )
                    status_data = resp.json()
                    status = status_data.get("status")

                    if status == "completed":
                        log("Task completed successfully!")

                        # Final server log pull
                        try:
                            resp = await client.get(
                                f"{server_url}/get_server_log",
                                params={"job_id": job_id, "offset": server_log_offset}
                            )
                            log_data = resp.json()
                            if log_data.get("content"):
                                with open(server_log_file, 'a') as f:
                                    f.write(log_data["content"])
                        except:
                            pass

                        # Download any remaining completed tasks
                        try:
                            resp = await client.get(
                                f"{server_url}/get_completed_tasks",
                                params={"job_id": job_id}
                            )
                            completed_data = resp.json()
                            task_names = completed_data.get("task_names", [])

                            if task_names:
                                log(f"Downloading {len(task_names)} remaining tasks")
                                for task_name in task_names:
                                    await download_task_if_needed(
                                        task_name, output_dir_path, server_url, job_id,
                                        record_manager, force_redownload, trust_env
                                    )
                        except Exception as e:
                            log(f"Warning: Failed to download remaining tasks: {e}")

                        # Download static files
                        await download_static_files(output_dir_path, server_url, job_id, trust_env)

                        log(f"All results saved to: {output_dir}")
                        log("="*60)
                        sys.exit(0)

                    elif status in ["failed", "timeout", "cancelled"]:
                        error = status_data.get("error", "Unknown error")
                        log(f"Task failed/cancelled: {error}")

                        # Final server log pull
                        try:
                            resp = await client.get(
                                f"{server_url}/get_server_log",
                                params={"job_id": job_id, "offset": server_log_offset}
                            )
                            log_data = resp.json()
                            if log_data.get("content"):
                                with open(server_log_file, 'a') as f:
                                    f.write(log_data["content"])
                        except:
                            pass

                        log("="*60)
                        sys.exit(1)

                    else:
                        elapsed_min = int(elapsed / 60)
                        log(f"Task running... (elapsed: {elapsed_min} minutes)")

                except Exception as e:
                    log(f"Error polling status: {e}")

                await asyncio.sleep(POLL_INTERVAL_PUBLIC)

    except KeyboardInterrupt:
        log("\n!!! Client interrupted by user (Ctrl+C)")
        await cancel_job_on_server(server_url, job_id, "Client interrupted", trust_env)
        sys.exit(1)
    except Exception as e:
        log(f"\n!!! FATAL ERROR in client: {e}")
        import traceback
        log(traceback.format_exc())
        await cancel_job_on_server(server_url, job_id, f"Client error: {e}", trust_env)
        sys.exit(1)

async def private_worker(
    server_url: str,
    job_id: str,
    client_id: str,
    vllm_url: str,
    vllm_api_key: Optional[str],
    ws_proxy_port: int,
    output_dir: str,
    force_redownload: bool,
    trust_env: bool = False
):
    """
    Background worker for private mode
    Starts simple_client_ws.py and monitors job status
    """
    # Derive all file paths from output_dir
    output_dir_path = Path(output_dir)
    log_file = str(output_dir_path / "client.log")
    server_log_file = str(output_dir_path / "server.log")

    # delete the old log files if exists
    if os.path.exists(log_file):
        os.remove(log_file)
    if os.path.exists(server_log_file):
        os.remove(server_log_file)

    setup_logging(log_file)

    log("="*60)
    log("Toolathlon Eval Client - Private Mode Worker")
    log(f"Job ID: {job_id}")
    log(f"Client ID: {client_id}")
    log(f"vLLM URL: {vllm_url}")
    log(f"Server: {server_url}")
    log(f"Output directory: {output_dir}")
    if force_redownload:
        log("Force redownload: ENABLED")
    log("="*60)

    # Initialize download record manager
    record_manager = DownloadRecordManager(output_dir_path)
    if force_redownload:
        log("Clearing download records for force redownload")
        record_manager.clear_all()

    ws_client_process = None
    ws_client_log_file = None

    # Setup signal handlers for graceful shutdown
    import signal

    def signal_handler(signum, frame):
        log(f"\n!!! Received signal {signum}, shutting down...")
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        start_time = time.time()
        server_log_offset = 0
        should_exit = False
        exit_code = 0

        # Extract server host from server_url for WebSocket connection
        parsed = urlparse(server_url)
        ws_server_url = f"http://{parsed.hostname}:{ws_proxy_port}"

        # Start simple_client_ws.py
        log(f"[WS] Starting WebSocket client...")
        log(f"[WS] Connecting to: {ws_server_url}")
        log(f"[WS] Job ID: {job_id}")
        ws_client_log = str(Path(log_file).parent / "ws_client.log")

        with open(ws_client_log, 'w') as log_f:
            ws_client_process = await asyncio.create_subprocess_exec(
                sys.executable, "simple_client_ws.py",
                "--server-url", ws_server_url,
                "--llm-base-url", vllm_url,
                *(["--llm-api-key", vllm_api_key] if vllm_api_key else []),
                "--job-id", job_id,  # Pass job_id for authentication
                stdout=log_f,
                stderr=asyncio.subprocess.STDOUT
            )

        log(f"[WS] WebSocket client started (PID: {ws_client_process.pid})")
        log(f"[WS] Client log: {ws_client_log}")

        async def status_poller():
            """Poll job status and sync server log"""
            nonlocal should_exit, exit_code, server_log_offset

            async with httpx.AsyncClient(timeout=30.0, trust_env=trust_env) as client:
                while not should_exit:
                    try:
                        elapsed = time.time() - start_time

                        # Check timeout
                        if elapsed > TIMEOUT_SECONDS:
                            log(f"ERROR: Task exceeded {TIMEOUT_SECONDS//60} minutes timeout")
                            await cancel_job_on_server(server_url, job_id, "Timeout", trust_env)
                            should_exit = True
                            exit_code = 1
                            return

                        # Pull server log
                        try:
                            resp = await client.get(
                                f"{server_url}/get_server_log",
                                params={"job_id": job_id, "offset": server_log_offset}
                            )
                            log_data = resp.json()

                            if log_data.get("content"):
                                with open(server_log_file, 'a') as f:
                                    f.write(log_data["content"])
                                server_log_offset = log_data["offset"]

                        except Exception as e:
                            log(f"Warning: Failed to fetch server log: {e}")

                        # Download completed tasks incrementally
                        try:
                            resp = await client.get(
                                f"{server_url}/get_completed_tasks",
                                params={"job_id": job_id}
                            )
                            completed_data = resp.json()
                            task_names = completed_data.get("task_names", [])

                            if task_names:
                                log(f"Found {len(task_names)} newly completed tasks")
                                for task_name in task_names:
                                    await download_task_if_needed(
                                        task_name, output_dir_path, server_url, job_id,
                                        record_manager, force_redownload, trust_env
                                    )
                        except Exception as e:
                            log(f"Warning: Failed to check/download completed tasks: {e}")

                        # Poll status
                        resp = await client.get(
                            f"{server_url}/poll_job_status",
                            params={"job_id": job_id}
                        )
                        status_data = resp.json()
                        status = status_data.get("status")

                        if status == "completed":
                            log("Task completed successfully!")

                            # Final server log pull
                            try:
                                resp = await client.get(
                                    f"{server_url}/get_server_log",
                                    params={"job_id": job_id, "offset": server_log_offset}
                                )
                                log_data = resp.json()
                                if log_data.get("content"):
                                    with open(server_log_file, 'a') as f:
                                        f.write(log_data["content"])
                            except:
                                pass

                            # Download any remaining completed tasks
                            try:
                                resp = await client.get(
                                    f"{server_url}/get_completed_tasks",
                                    params={"job_id": job_id}
                                )
                                completed_data = resp.json()
                                task_names = completed_data.get("task_names", [])

                                if task_names:
                                    log(f"Downloading {len(task_names)} remaining tasks")
                                    for task_name in task_names:
                                        await download_task_if_needed(
                                            task_name, output_dir_path, server_url, job_id,
                                            record_manager, force_redownload, trust_env
                                        )
                            except Exception as e:
                                log(f"Warning: Failed to download remaining tasks: {e}")

                            # Download static files
                            await download_static_files(output_dir_path, server_url, job_id, trust_env)

                            log(f"All results saved to: {output_dir}")
                            log("="*60)

                            should_exit = True
                            exit_code = 0
                            return

                        elif status in ["failed", "timeout", "cancelled"]:
                            error = status_data.get("error", "Unknown error")
                            log(f"Task failed/cancelled: {error}")

                            # Final server log pull
                            try:
                                resp = await client.get(
                                    f"{server_url}/get_server_log",
                                    params={"job_id": job_id, "offset": server_log_offset}
                                )
                                log_data = resp.json()
                                if log_data.get("content"):
                                    with open(server_log_file, 'a') as f:
                                        f.write(log_data["content"])
                            except:
                                pass

                            log("="*60)
                            should_exit = True
                            exit_code = 1
                            return

                        else:
                            elapsed_min = int(elapsed / 60)
                            if elapsed_min % 5 == 0:  # Log every 5 minutes
                                log(f"Task running... (elapsed: {elapsed_min} minutes)")

                    except Exception as e:
                        log(f"Error in status poller: {e}")

                    await asyncio.sleep(POLL_INTERVAL_PRIVATE)

        # Run status poller
        await status_poller()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        log("\n!!! Client interrupted by user (Ctrl+C)")
        await cancel_job_on_server(server_url, job_id, "Client interrupted", trust_env)
        sys.exit(1)
    except Exception as e:
        log(f"\n!!! FATAL ERROR in client: {e}")
        import traceback
        log(traceback.format_exc())
        await cancel_job_on_server(server_url, job_id, f"Client error: {e}", trust_env)
        sys.exit(1)
    finally:
        # Kill WebSocket client if running
        if ws_client_process:
            try:
                log(f"[WS] Stopping WebSocket client (PID: {ws_client_process.pid})")
                ws_client_process.kill()
                await ws_client_process.wait()
            except:
                pass

# ===== CLI Commands =====

@app.command()
def run(
    server_host: str = typer.Option(
        ...,
        help=f"Toolathlon evaluation server hostname"
    ),
    server_port: int = typer.Option(
        DEFAULT_SERVER_PORT,
        help=f"Toolathlon evaluation server port (default: {DEFAULT_SERVER_PORT})"
    ),
    mode: str = typer.Option(
        ...,
        help="Evaluation mode: 'public' (use public OpenAI-compatible API) or 'private' (use locally-deployed e.g. vLLM/SGLang via WebSocket)"
    ),
    base_url: str = typer.Option(
        ...,
        help="API base URL. Public mode: e.g., 'https://api.openai.com/v1'. Private mode: local vLLM address e.g., 'http://localhost:8000'"
    ),
    model_name: str = typer.Option(
        ...,
        help="Model name to evaluate. Examples: 'gpt-5', 'deepseek-chat', this should be accessible via the base_url"
    ),
    output_dir: str = typer.Option(
        ...,
        help="Output directory for logs and results. Will contain: client.log, server.log, finalpool/, eval_stats.json, etc."
    ),
    api_key: Optional[str] = typer.Option(
        None,
        help="API key for authentication. It is required for public mode. In private mode it is not sent to the evaluation server; it is forwarded to the local WebSocket client, which otherwise falls back to the TOOLATHLON_OPENAI_API_KEY or OPENAI_API_KEY environment variable."
    ),
    workers: int = typer.Option(
        10,
        help="Number of parallel workers for task execution (default: 10). Higher values = faster but more resource-intensive"
    ),
    ws_proxy_port: int = typer.Option(
        DEFAULT_WS_PROXY_PORT,
        help=f"WebSocket proxy port for private mode (default: {DEFAULT_WS_PROXY_PORT})"
    ),
    job_id: Optional[str] = typer.Option(
        None,
        help="Custom job ID (optional). If not provided, a UUID will be generated. Use same job_id to resume incomplete tasks"
    ),
    force_redownload: bool = typer.Option(
        False,
        help="Force redownload all task results and files, overwriting existing ones (useful for resuming with fresh data)"
    ),
    model_params_file: Optional[str] = typer.Option(
        None,
        help="Path to JSON file with custom model parameters (e.g., temperature, top_p, max_tokens) that are acceptable for your /chat/completions endpoint. Format: {\"temperature\": 0.7, \"top_p\": 0.95}. If not provided, the default parameters will be used."
    ),
    task_list_file: Optional[str] = typer.Option(
        None,
        help="Path to text file with task names (one per line) to evaluate only a subset of tasks. Example: task1.txt containing 'ab-testing\\nadd-bibtex\\n...'"
    ),
    skip_container_restart: bool = typer.Option(
        False,
        help="⚠️  Skip Docker container restart. ONLY use for debugging/testing small task subsets. NOT recommended for complete evaluation"
    ),
    override_output_dir: bool = typer.Option(
        False,
        help="Override and clear output directory if it exists and is not empty. If False (default), will error if output directory is not empty"
    ),
    provider: str = typer.Option(
        "unified",
        help="Model provider type. Supported values: 'unified' (default, OpenAI-compatible API), 'openai_stateful_responses' (OpenAI Responses API with stateful context management)"
    ),
    trust_env_in_httpx: bool = typer.Option(
        False,
        help="If enabled, httpx will trust environment proxy settings (HTTP_PROXY, HTTPS_PROXY, etc.)"
    ),
):
    """
    Submit and run a Toolathlon evaluation task.

    \b
    MODES:
      • public  - Use public OpenAI-compatible APIs (OpenAI, Anthropic, OpenRouter, etc.)
      • private - Use local vLLM server via WebSocket proxy

    \b
    WORKFLOW:
      1. Submit evaluation task to Toolathlon server
      2. Start background worker process (non-blocking)
      3. Worker monitors progress and downloads results incrementally
      4. Returns immediately - use 'tail -f <output_dir>/client.log' to monitor

    \b
    EXAMPLES:
      # Public mode with OpenAI
      python eval_client.py run \\
        --mode public \\
        --base-url "https://api.openai.com/v1" \\
        --api-key "sk-..." \\
        --model-name "gpt-5" \\
        --output-dir "./results/gpt5"

      # Private mode with local vLLM
      python eval_client.py run \\
        --mode private \\
        --base-url "http://localhost:8000" \\
        --model-name "your-model-name" \\
        --output-dir "./results/your-model-name"

      # Test subset of tasks with custom parameters
      python eval_client.py run \\
        --mode public \\
        --base-url "https://api.openai.com/v1" \\
        --model-name "gpt-4" \\
        --output-dir "./results/test" \\
        --task-list-file "./test_tasks.txt" \\
        --model-params-file "./params.json" \\
        --skip-container-restart

    \b
    FILE FORMATS:
      task_list.txt - One task name per line:
        ab-testing
        find-alita-paper
        git-milestone

      model_params.json - Custom parameters:
        {
          "temperature": 0.7,
          "top_p": 0.95,
          "max_tokens": 4096
        }

    \b
    OUTPUT FILES:
      <output_dir>/
        ├── client.log              - Client execution log (monitor with 'tail -f')
        ├── server.log              - Server execution log (synced from server)
        ├── eval_stats.json         - Final evaluation statistics
        ├── traj_log_all.jsonl      - Trajectory logs for all tasks
        ├── finalpool/              - Individual task results (downloaded incrementally)
        │   ├── task_name_1/
        │   ├── task_name_2/
        │   └── ...
        └── ws_client.log           - WebSocket client log (private mode only)

    \b
    NOTES:
      ⚠️  --skip-container-restart should ONLY be used for:
          • Debugging and development
          • Testing small subsets of tasks
          For complete evaluation, always restart containers for clean environment

      🔍 Check task status:
          python eval_client.py status --job-id <job_id> --server-host <host> --server-port <port>
          check more usage details via "python eval_client.py status --help"

      🛑 Cancel running task:
          python eval_client.py cancel --job-id <job_id> --server-host <host> --server-port <port>
          check more usage details via "python eval_client.py cancel --help"
    """

    if mode not in ["public", "private"]:
        typer.echo("Error: mode must be 'public' or 'private'", err=True)
        raise typer.Exit(1)

    # Validate and load model parameters file if provided
    model_params = None
    if model_params_file:
        model_params_path = Path(model_params_file)

        # Check if file exists
        if not model_params_path.exists():
            typer.echo(f"Error: Model parameters file not found: {model_params_file}", err=True)
            raise typer.Exit(1)

        # Try to load and parse JSON
        try:
            with open(model_params_path, 'r') as f:
                model_params = json.load(f)

            if not isinstance(model_params, dict):
                typer.echo(f"Error: Model parameters file must contain a JSON object (dict), got {type(model_params)}", err=True)
                raise typer.Exit(1)

            typer.echo(f"Loaded model parameters from: {model_params_file}")
            typer.echo(f"  Parameters: {json.dumps(model_params, indent=2)}")

        except json.JSONDecodeError as e:
            typer.echo(f"Error: Failed to parse model parameters file as JSON: {e}", err=True)
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"Error: Failed to read model parameters file: {e}", err=True)
            raise typer.Exit(1)

    # Validate and load task list file if provided
    task_list_content = None
    if task_list_file:
        task_list_path = Path(task_list_file)

        # Check if file exists
        if not task_list_path.exists():
            typer.echo(f"Error: Task list file not found: {task_list_file}", err=True)
            raise typer.Exit(1)

        # Try to read task list
        try:
            with open(task_list_path, 'r', encoding='utf-8') as f:
                task_list_content = f.read()

            # Count and validate tasks
            tasks = [line.strip() for line in task_list_content.strip().split('\n') if line.strip()]
            if not tasks:
                typer.echo(f"Error: Task list file is empty: {task_list_file}", err=True)
                raise typer.Exit(1)

            typer.echo(f"Loaded task list from: {task_list_file}")
            typer.echo(f"  Number of tasks: {len(tasks)}")

        except Exception as e:
            typer.echo(f"Error: Failed to read task list file: {e}", err=True)
            raise typer.Exit(1)

    # Display warning if skip_container_restart is enabled
    if skip_container_restart:
        typer.echo("\n" + "="*60)
        typer.echo("⚠️  WARNING: Container restart will be SKIPPED")
        typer.echo("="*60)
        typer.echo("This is recommended ONLY for:")
        typer.echo("  - Debugging purposes")
        typer.echo("  - Testing a small number of tasks")
        typer.echo("\nFor complete evaluation, it is STRONGLY recommended")
        typer.echo("to restart containers to ensure a clean environment.")
        typer.echo("="*60 + "\n")

    # Handle output directory
    output_dir_path = Path(output_dir)

    # Check if directory exists and is not empty
    if output_dir_path.exists():
        # Check if directory has any contents
        dir_contents = list(output_dir_path.iterdir())
        if dir_contents:
            if override_output_dir:
                # Clear the directory
                typer.echo(f"\n⚠️  Clearing existing output directory: {output_dir}")
                typer.echo(f"   Found {len(dir_contents)} items, removing all...")
                import shutil
                shutil.rmtree(output_dir_path)
                output_dir_path.mkdir(parents=True, exist_ok=True)
                typer.echo(f"   ✓ Directory cleared and recreated\n")
            else:
                # Error - directory not empty and override not set
                typer.echo(f"\n❌ Error: Output directory is not empty: {output_dir}", err=True)
                typer.echo(f"   Found {len(dir_contents)} items:", err=True)
                for item in dir_contents[:5]:  # Show first 5 items
                    typer.echo(f"     - {item.name}", err=True)
                if len(dir_contents) > 5:
                    typer.echo(f"     ... and {len(dir_contents) - 5} more", err=True)
                typer.echo(f"\n💡 Options:", err=True)
                typer.echo(f"   1. Use a different output directory", err=True)
                typer.echo(f"   2. Manually clear the directory", err=True)
                typer.echo(f"   3. Use --override-output-dir to automatically clear it", err=True)
                raise typer.Exit(1)
    else:
        # Directory doesn't exist, create it
        output_dir_path.mkdir(parents=True, exist_ok=True)

    # Build server URL
    server_url = f"http://{server_host}:{server_port}"

    typer.echo("Submitting evaluation task to server...")
    typer.echo(f"  Mode: {mode}")
    typer.echo(f"  Model: {model_name}")
    typer.echo(f"  Workers: {workers}")
    typer.echo(f"  Server: {server_url}")
    if mode == "private":
        typer.echo(f"  WebSocket Proxy Port: {ws_proxy_port}")

    # Submit task
    try:
        import httpx

        with httpx.Client(timeout=30.0, trust_env=trust_env_in_httpx) as client:
            submit_data = {
                "client_version": CLIENT_VERSION,  # Send client version for compatibility check
                "mode": mode,
                "base_url": base_url,
                # The server never reads the key for private jobs; inference
                # is proxied through the local WebSocket client.
                "api_key": api_key if mode == "public" else None,
                "model_name": model_name,
                "workers": workers,
                "custom_job_id": job_id,  # Pass custom job_id if provided
                "skip_container_restart": skip_container_restart,
                "provider": provider  # Add provider field (v1.1+)
            }

            # Add ws_client_version if in private mode
            if mode == "private" and WS_CLIENT_VERSION:
                submit_data["ws_client_version"] = WS_CLIENT_VERSION

            # Add model_params if provided
            if model_params:
                submit_data["model_params"] = model_params

            # Add task_list_content if provided
            if task_list_content:
                submit_data["task_list_content"] = task_list_content

            resp = client.post(
                f"{server_url}/submit_evaluation",
                json=submit_data
            )

            if resp.status_code != 200:
                error_data = resp.json()
                detail = error_data.get('detail', 'Unknown error')

                # Handle detailed error responses (dict)
                if isinstance(detail, dict):
                    error_type = detail.get('error', 'Error')
                    message = detail.get('message', 'Unknown error')

                    typer.echo(f"\n❌ {error_type}:", err=True)
                    typer.echo(f"   {message}", err=True)

                    # Version missing error (old client)
                    if error_type == "Client version missing":
                        server_version = detail.get('server_version', 'unknown')
                        typer.echo(f"\n   Server version: {server_version}", err=True)
                        typer.echo(f"   (Client version is defined at the top of eval_client.py)", err=True)

                    # Version compatibility error
                    elif error_type == "Client version not supported":
                        supported = detail.get('supported_versions', [])
                        typer.echo(f"\n   Your client version: {CLIENT_VERSION}", err=True)
                        typer.echo(f"   Supported versions: {', '.join(supported)}", err=True)
                        typer.echo(f"   (Version is defined at the top of eval_client.py)", err=True)

                    # WebSocket client version errors (private mode)
                    elif error_type in {"WebSocket client version missing", "WebSocket client version not supported"}:
                        supported = detail.get('supported_ws_client_versions', [])
                        your_ws_version = detail.get('your_ws_client_version')
                        if your_ws_version:
                            typer.echo(f"\n   Your WebSocket client version: {your_ws_version}", err=True)
                        if supported:
                            typer.echo(f"   Supported WebSocket client versions: {', '.join(supported)}", err=True)
                        typer.echo(f"   (WebSocket client version is defined at the top of simple_client_ws.py)", err=True)

                    # Workers limit error
                    elif error_type == "Workers limit exceeded":
                        max_workers = detail.get('max_workers', 'unknown')
                        typer.echo(f"\n   Server allows maximum {max_workers} workers", err=True)
                        typer.echo(f"   Please reduce --workers to {max_workers} or less", err=True)

                    action = detail.get('action')
                    if action:
                        typer.echo(f"\n   ⚠️  Update required:", err=True)
                        typer.echo(f"   {action}", err=True)
                else:
                    # Simple string error
                    typer.echo(f"\n❌ Task submission failed:", err=True)
                    typer.echo(f"   {detail}", err=True)

                raise typer.Exit(1)

            result = resp.json()
            final_job_id = result["job_id"]
            client_id = result.get("client_id")
            warning = result.get("warning")

    except httpx.ConnectError:
        typer.echo(f"\n❌ Cannot connect to server at {server_url}", err=True)
        typer.echo("   Please check if the server is running.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"\n❌ Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo("\n✓ Task submitted successfully!")
    typer.echo(f"  Job ID: {final_job_id}")
    if client_id:
        typer.echo(f"  Client ID: {client_id}")
    if task_list_content:
        task_count = len([line.strip() for line in task_list_content.strip().split('\n') if line.strip()])
        typer.echo(f"  Custom task list: {task_count} tasks")
    if skip_container_restart:
        typer.echo(f"  ⚠️  Container restart: SKIPPED")

    # Display warning if job_id already exists
    if warning:
        typer.echo(f"\n⚠️  WARNING: {warning}", err=False)
        typer.echo(f"   Only use the same job ID if you want to resume an incomplete task.", err=False)

    # Display rate limit information
    rate_limit_info = result.get("rate_limit_info")
    if rate_limit_info:
        typer.echo(f"\n📊 Rate Limit Status:")
        limit_mode = rate_limit_info.get("limit_mode")
        usage = rate_limit_info.get("usage", {})

        if limit_mode == "unlimited":
            typer.echo(f"  🎉 No rate limits applied")
        else:
            # Display duration info
            duration_info = usage.get("duration")
            if duration_info and duration_info != "unlimited":
                used_min = duration_info.get("used_minutes", 0)
                remaining_min = duration_info.get("remaining_minutes", 0)
                limit_min = duration_info.get("limit_minutes", 0)
                typer.echo(f"  ⏱️  Duration: {used_min:.1f} / {limit_min} minutes used ({remaining_min:.1f} remaining)")
            elif duration_info == "unlimited":
                typer.echo(f"  ⏱️  Duration: Unlimited")

            # Display request count info
            request_info = usage.get("requests")
            if request_info and request_info != "unlimited":
                used_req = request_info.get("used", 0)
                remaining_req = request_info.get("remaining", 0)
                limit_req = request_info.get("limit", 0)
                typer.echo(f"  📝 Requests: {used_req} / {limit_req} used ({remaining_req} remaining)")
            elif request_info == "unlimited":
                typer.echo(f"  📝 Requests: Unlimited")

    # Start background worker using subprocess with nohup-like behavior
    import subprocess

    # Build Python code to run worker directly
    if mode == "public":
        worker_code = f"""
import asyncio
import sys
sys.path.insert(0, '{os.path.abspath(os.path.dirname(__file__))}')
from eval_client import public_worker
asyncio.run(public_worker('{server_url}', '{final_job_id}', '{output_dir}', {force_redownload}, {trust_env_in_httpx}))
"""
    else:  # private
        # The key is handed to the worker via its environment, not its argv.
        worker_code = f"""
import asyncio
import sys
sys.path.insert(0, '{os.path.abspath(os.path.dirname(__file__))}')
from eval_client import private_worker
asyncio.run(private_worker('{server_url}', '{final_job_id}', '{client_id}', '{base_url}', None, {ws_proxy_port}, '{output_dir}', {force_redownload}, {trust_env_in_httpx}))
"""

    worker_env = os.environ.copy()
    if mode == "private" and api_key:
        worker_env["TOOLATHLON_OPENAI_API_KEY"] = api_key

    # Start detached background process
    process = subprocess.Popen(
        [sys.executable, '-c', worker_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd=os.getcwd(),
        env=worker_env
    )

    typer.echo(f"\n✓ Background worker started (PID: {process.pid})")
    typer.echo(f"  Output directory: {output_dir}")
    typer.echo(f"  - client.log (client execution log)")
    typer.echo(f"  - server.log (server execution log, syncing...)")
    typer.echo(f"  - eval_stats.json (results, when complete)")
    typer.echo(f"  - traj_log_all.jsonl (trajectory log, when complete)")
    typer.echo(f"  - finalpool/ (individual task results, downloading incrementally...)")
    if mode == "private":
        typer.echo(f"  - ws_client.log (WebSocket client log)")
    if force_redownload:
        typer.echo(f"\n⚠️  Force redownload enabled: all files will be redownloaded")
    typer.echo(f"\n📊 Monitor progress:")
    typer.echo(f"  tail -f {output_dir}/client.log")
    typer.echo(f"\n❓ Check status:")
    typer.echo(f"  python eval_client.py status --job-id {final_job_id} --server-host {server_host} --server-port {server_port}")
    typer.echo(f"\n🛑 Cancel task:")
    typer.echo(f"  python eval_client.py cancel --job-id {final_job_id} --server-host {server_host} --server-port {server_port}")
    typer.echo()

@app.command()
def status(
    job_id: str = typer.Option(..., help="Job ID to check. You can find it from the 'run' command output or from the client.log file."),
    server_host: str = typer.Option(..., help=f"Evaluation server hostname"),
    server_port: int = typer.Option(DEFAULT_SERVER_PORT, help=f"Evaluation server port (default: {DEFAULT_SERVER_PORT})"),
):
    """
    Check the status of a submitted evaluation task.

    \b
    Returns current status:
      • running   - Task is currently executing
      • completed - Task finished successfully
      • failed    - Task failed with error
      • timeout   - Task exceeded time limit
      • cancelled - Task was manually cancelled

    \b
    EXAMPLE:
      python eval_client.py status --job-id job_abc123def456 --server-host {server_host} --server-port {server_port}
    """

    server_url = f"http://{server_host}:{server_port}"

    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{server_url}/poll_job_status",
                params={"job_id": job_id}
            )

            if resp.status_code != 200:
                typer.echo(f"Error: {resp.json()}", err=True)
                raise typer.Exit(1)

            data = resp.json()
            status = data.get("status")

            typer.echo(f"\nJob ID: {job_id}")
            typer.echo(f"Status: {status}")

            if status == "completed":
                typer.echo("✓ Task completed successfully!")
            elif status in ["failed", "timeout"]:
                typer.echo(f"✗ Task failed: {data.get('error', 'Unknown')}")
            elif status == "running":
                typer.echo("⏳ Task is still running...")
            else:
                typer.echo("? Status unknown (task may not exist)")

            typer.echo()

    except httpx.ConnectError:
        typer.echo(f"Cannot connect to server at {server_url}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def cancel(
    job_id: str = typer.Option(..., help="Job ID to cancel. You can find it from the 'run' command output or from the client.log file."),
    server_host: str = typer.Option(..., help=f"Evaluation server hostname"),
    server_port: int = typer.Option(DEFAULT_SERVER_PORT, help=f"Evaluation server port (default: {DEFAULT_SERVER_PORT})"),
):
    """
    Cancel a running evaluation task.

    \b
    This will:
      • Kill the evaluation process on the server
      • Stop and remove all Docker containers for this task
      • Mark the task as cancelled

    \b
    NOTE: The client-side background worker will detect cancellation
          and stop automatically within a few seconds.

    \b
    EXAMPLE:
      python eval_client.py cancel job_abc123def456 --server-host {server_host} --server-port {server_port}
    """

    server_url = f"http://{server_host}:{server_port}"

    try:
        import httpx

        typer.echo(f"Cancelling job {job_id}...")

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{server_url}/cancel_job",
                params={"job_id": job_id}
            )

            if resp.status_code == 200:
                typer.echo(f"✓ Job {job_id} cancelled successfully")
                typer.echo(f"  - Process killed")
                typer.echo(f"  - Docker containers stopped and removed")
            elif resp.status_code == 400:
                # Job exists but not running (completed or cancelled)
                error = resp.json()
                typer.echo(f"ℹ️  {error.get('detail', 'Job is not running')}")
                typer.echo(f"\n💡 Tip: Use 'status' command to check job status:")
                typer.echo(f"   python eval_client.py status {job_id} {server_host} --server-port {server_port}")
                raise typer.Exit(0)  # Exit with 0 since this is not really an error
            elif resp.status_code == 404:
                # Job not found
                error = resp.json()
                typer.echo(f"❌ {error.get('detail', 'Job not found')}", err=True)
                typer.echo(f"\n💡 Tip: Check if the job ID is correct", err=True)
                raise typer.Exit(1)
            else:
                error = resp.json()
                typer.echo(f"❌ Error: {error.get('detail', 'Unknown error')}", err=True)
                raise typer.Exit(1)

    except httpx.ConnectError:
        typer.echo(f"❌ Cannot connect to server at {server_url}", err=True)
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        # This shouldn't happen since we're checking status codes above, but just in case
        typer.echo(f"❌ HTTP Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def check(
    server_host: str = typer.Option(..., help=f"Evaluation server hostname"),
    server_port: int = typer.Option(DEFAULT_SERVER_PORT, help=f"Evaluation server port (default: {DEFAULT_SERVER_PORT})"),
):
    """
    Check if the Toolathlon evaluation server is available and idle.

    \b
    Use this before submitting a new task to verify:
      • Server is reachable
      • Server is not currently processing another task

    \b
    Server can only handle one evaluation task at a time.
    If busy, it will show the current job's anonymized ID and start time.

    \b
    EXAMPLE:
      python eval_client.py check --server-host {server_host} --server-port {server_port}
    """

    server_url = f"http://{server_host}:{server_port}"

    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{server_url}/check_server_status")

            if resp.status_code != 200:
                typer.echo("Error checking server status", err=True)
                raise typer.Exit(1)

            data = resp.json()

            if data.get("busy"):
                job_id = data.get('job_id', '')
                anonymized_id = anonymize_job_id(job_id)
                typer.echo("⏳ Server is currently busy")
                typer.echo(f"   Job ID: {anonymized_id}")
                typer.echo(f"   Mode: {data.get('mode')}")
                typer.echo(f"   Started: {data.get('started_at')}")
                typer.echo("\nPlease try again later.")
            else:
                typer.echo("✓ Server is idle and ready to accept tasks")

    except httpx.ConnectError:
        typer.echo(f"❌ Cannot connect to server at {server_url}", err=True)
        typer.echo("   Please check if the server is running.", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
