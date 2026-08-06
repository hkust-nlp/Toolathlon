# Toolathlon Remote Evaluation Service

Besides configuring Toolathlon evaluation on your own machine, we also provide Toolathlon evaluation as a service on public servers, where we have setup all the required MCP accounts and you don't need to worry about the setup -- you don't even need to install any MCP-related dependencies, evaluation can be ran by just communicating with our public server.

> We have set up a public Toolathlon evaluation service on 47.253.6.47, this is mainly for you to quickly play with our evaluation without any setup. However, to ensure fair usage and prevent abuse, we have implemented a dual-limit rate limiting system on this public service:
> - **Duration limit**: 180 minutes cumulative execution time per IP per 24 hours
> - **Request count limit**: 3 evaluation requests per IP per 24 hours
> - **Logic**: If your cumulative execution time is under 180 minutes, you can submit unlimited requests (great for debugging!). Once you exceed 180 minutes, the request count limit applies.
>
> If you find this public service too restrictive or crowded, you have a few other options:
> 1. Setup your own Toolathlon evaluation service on your own machine following the main readme, which would take like 20-30 minutes.
> 2. If you are a major user that will use Toolathlon evaluation a lot, please contact us (jlini@cse.ust.hk), we may be able to provide a dedicated evaluation service for you (for free).
> 3. If you have an API endpoint and just want to test your model, please contact us (jlini@cse.ust.hk) and we are happy to help you run evaluation on Toolathlon with your given API endpoint.

---

## Quick Start

### Installation

If you want to test **your inhouse locally deployed model that is not publicly accessible**, just simply put `eval_client.py` and `simple_client_ws.py` together under a folder on your own machine (they are already there if you cloned this repo), then install the client-side dependencies:

```bash
pip install httpx typer websockets
# Or use uv
uv add httpx typer websockets
```

### Private Mode (Local OpenAI-ChatCompletion endpoint via vLLM/SGLang etc)

For locally deployed models that are not publicly accessible:

```bash
# Debug running for only one task:
cat > debug_tasks.txt << EOF
find-alita-paper
EOF

python eval_client.py run \
  --mode private \
  --base-url http://localhost:8000/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key dummy \
  --workers 10 \
  --server-port 8080 \
  --ws-proxy-port 8081 \
  --task-list-file ./debug_tasks.txt \
  --skip-container-restart

```

If the debug run works fine, then you are ready to launch the full eval on all tasks: 

```bash
python eval_client.py run \
  --mode private \
  --base-url http://localhost:8000/v1 \
  --model-name your-model-name \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key dummy \
  --workers 10 \
  --server-port 8080 \
  --ws-proxy-port 8081
```


### Public Mode (Pubic OpenAI-ChatCompletion endpoint from OpenAI/Anthropic/etc.)

For ready-to-use public API endpoints:

```bash
# it is recommended to launch a debug run as above before 
# the full eval run below
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-5 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-your-api-key \
  --workers 10 \
  --server-port 8080
```

If the server is idle, your task will be submitted and you will find the results later in the `./results` directory. Otherwise, please wait for a while and check again later via:

```bash
python eval_client.py check --server-host 47.253.6.47 --server-port 8080
```

for more details, please use the following commands:
```
python eval_client.py run --help
python eval_client.py check --help
python eval_client.py cancel --help
python eval_client.py status --help
```

---


## Advanced Features

### Model Provider Selection (v1.1+)

Choose the appropriate provider based on your API endpoint type:

**Supported Providers:**
- `unified` (default) - Standard OpenAI-compatible APIs (OpenAI, Anthropic, OpenRouter, etc.)
- `openai_stateful_responses` - OpenAI Responses API with automatic stateful context management

**Usage:**

```bash
# Default: unified provider (no need to specify)
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-...

# Explicit unified provider
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --provider unified

# OpenAI Responses API with stateful context
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --provider openai_stateful_responses
```

**When to use `openai_stateful_responses`:**
- ✓ Using OpenAI's Responses API (not Chat Completions API)
- ✓ Want automatic context management (no manual `manage_context` tool)
- ✓ Working with stateful conversation history

**Note:** The `manage_context` local tool is automatically disabled when using `openai_stateful_responses` provider, as context is managed by the API itself.

### Proxy Environment Support (Optional)

If you're behind a corporate proxy or need to use environment variables for HTTP/HTTPS proxies, enable the `--trust_env_in_httpx` flag:

**Usage:**

```bash
# Set proxy environment variables (if not already set)
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1

# Run evaluation with proxy support
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --trust_env_in_httpx
```

**Behavior:**
- Without flag: httpx ignores environment proxy settings (default)
- With flag: httpx reads and uses `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY` environment variables

**When to use:**
- ✓ Behind a corporate proxy
- ✓ Need to route traffic through a specific proxy server
- ✓ Using environment-based proxy configuration
- ✗ No proxy needed (default behavior is fine)

**Note:** This flag affects all HTTP/HTTPS requests made by the client, including:
- Server communication (submit task, check status, etc.)
- Task result downloads
- Server log fetching

### Custom Model Parameters (Optional)

Override default model parameters except "model","messages","tools","tool_choice" and "stream" (see `utils/api_model/model_provider.py` for more details), which means the final completion params = these 5 automatically generated by agnt scaffold + your provided params:

```bash
# Create params.json
cat > model_params.json << EOF
{
  "temperature": 0.7,
  "top_p": 0.95,
  "max_tokens": 4096
}
EOF

# Use with eval
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --model-params-file ./model_params.json
```

### Test Subset of Tasks (Optional)

Run evaluation on specific tasks only:

```bash
# Create task list
cat > my_tasks.txt << EOF
ab-testing
find-alita-paper
git-milestone
EOF

# Use with eval
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --task-list-file ./my_tasks.txt
```

**Note:** Each line in the task list file should be a task name. Empty lines are ignored.

### Skip Container Restart (Debugging Only, Optional)

⚠️ **For debugging/testing small subsets only. NOT recommended for complete evaluation.**

```bash
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --task-list-file ./debug_tasks.txt \
  --skip-container-restart
```

**When to use:**
- ✓ Debugging specific issues
- ✓ Testing 1-2 tasks quickly
- ✗ Complete evaluation (always restart containers for clean environment)

### Override Output Directory (Optional)

By default, the client will error if the output directory is not empty. Use `--override-output-dir` to automatically clear it:

```bash
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --override-output-dir
```

**Behavior:**
- Without flag: Error if directory is not empty
- With flag: Automatically clear and recreate directory

### Resume Incomplete Tasks (Optional)

If your evaluation was interrupted (e.g., network issues, client/server crash), you can resume it by providing the same job ID:

```bash
python eval_client.py run \
  --mode public \
  --base-url https://api.openai.com/v1 \
  --model-name gpt-4 \
  --output-dir ./results \
  --server-host 47.253.6.47 \
  --api-key sk-... \
  --job-id job_abc123def456  # Use the same job ID to resume
```

**Note:**
- You can find your job ID from the initial submission output or from your client.log
- The server will output a warning if the job ID already exists, but will accept the request
- Results will be written to the same output directory on server
- This works for both public and private modes

---

## Monitoring & Management

### Check Server Status

```bash
python eval_client.py check --server-host 47.253.6.47 --server-port 8080
```

**Output (idle):**
```
✓ Server is idle and ready to accept tasks
```

**Output (busy):**
```
⏳ Server is currently busy
   Job ID: job_ab*****56
   Mode: public
   Started: 2025-12-04T10:30:45.123456

Please try again later.
```

### Monitor Progress

```bash
# Watch client log (real-time)
tail -f ./results/client.log

# Watch server execution log (synced in real-time)
tail -f ./results/server.log
```

### Check Task Status

```bash
python eval_client.py status --job-id job_abc123def456 --server-host 47.253.6.47 --server-port 8080
```

**Possible statuses:**
- `running` - Task is currently executing
- `completed` - Task finished successfully
- `failed` - Task failed with error
- `timeout` - Task exceeded time limit (240 minutes)
- `cancelled` - Task was manually cancelled

### Cancel Running Task

```bash
python eval_client.py cancel job_abc123def456 --server-host 47.253.6.47 --server-port 8080
```

**This will:**
- Kill the evaluation process
- Stop and remove all Docker containers
- Clean up server resources

**Note:** If you try to cancel a completed task, you'll get a friendly message:
```
ℹ️  Job has already completed. Cannot cancel a completed job.

💡 Tip: Use 'status' command to check job status:
   python eval_client.py status job_abc123def456 47.253.6.47 --server-port 8080
```

---

## Output Files

When a task completes, the output directory will contain:

```
./results/
├── client.log              - Client execution log (monitor with 'tail -f')
├── server.log              - Server execution log (synced from server)
├── eval_stats.json         - Final evaluation statistics
├── traj_log_all.jsonl      - Trajectory logs for all tasks
├── finalpool/              - Individual task results (downloaded incrementally)
│   ├── task_name_1/
│   ├── task_name_2/
│   └── ...
└── ws_client.log           - WebSocket client log (private mode only)
```

**File descriptions:**

1. **eval_stats.json**
   - Evaluation statistics and results
   - Contains pass/fail status for all tasks

2. **traj_log_all.jsonl**
   - Complete trajectory logs for all tasks
   - One JSON object per line, each representing one task

3. **client.log**
   - Client-side execution log with timestamps
   - Shows task submission, status polling, completion

4. **server.log**
   - Server-side execution log (synced in real-time)
   - Shows container deployment, parallel test execution

5. **finalpool/**
   - Individual task results and artifacts
   - Downloaded incrementally as tasks complete
   - Each subdirectory contains complete task output

6. **ws_client.log** (private mode only)
   - WebSocket client log
   - Shows WebSocket connection status and request handling

---

## Architecture

### Public Mode
```
Client → Server → OpenAI/Anthropic/etc. API
```
Client submits task with API credentials. Server runs evaluation using the public API.

### Private Mode
```
Client + Local LLM ←→ WebSocket ←→ Server
```
Server runs evaluation but forwards LLM requests back to client via WebSocket. Your LLM credentials never leave your machine.

**How Private Mode Works:**
1. Server starts `simple_server_ws.py` (WebSocket proxy on port 8081)
2. Client starts `simple_client_ws.py` (connects to proxy)
3. When server needs LLM inference, request flows: Server → WebSocket → Client → Your LLM
4. Response flows back: Your LLM → Client → WebSocket → Server

---

## Privacy & Security

### Public Mode
- ⚠️ API keys are sent to server for making requests
- ⚠️ Server does not permanently store API keys
- 💡 Use HTTPS in production to protect credentials
- Server uses your API key to call LLM directly

### Private Mode
- ✓ LLM URL and API key stay on client machine
- ✓ Server never sees your credentials
- ✓ Only inference requests/responses transmitted
- Server's `TOOLATHLON_OPENAI_BASE_URL` points to local WebSocket proxy

### Job ID Anonymization
When checking server status, job IDs are anonymized:
- `job_abc123def456` → `job_ab*****56`
- First 6 and last 2 characters shown
- Protects running task privacy

### Rate Limiting

The server implements a dual-limit rate limiting system to ensure fair usage:

#### Rate Limit Modes

**1. Dual Limit Mode (Default)**
- **Duration Limit**: Maximum cumulative execution time per IP (e.g., 180 minutes)
- **Request Count Limit**: Maximum number of submissions per IP (e.g., 3 requests)
- **Logic**: If cumulative execution time < duration limit → unlimited submissions allowed (for debugging). Once duration limit exceeded → request count limit applies.

**2. Duration-Only Mode**
- Only limits total execution time
- Request count is unlimited
- Set by passing `-1` for request count parameter

**3. Count-Only Mode**
- Only limits number of submissions
- Execution time is unlimited
- Set by passing `-1` for duration parameter

**4. Unlimited Mode**
- No restrictions on either duration or request count
- Set by passing `-1` for both parameters

#### How It Works

When you submit a task, the server tracks:
- Your IP address
- Each job's start time and duration
- Your cumulative execution time within the 24-hour window

**Example (Dual Limit: 180 minutes + 3 requests):**
```
User A submits 5 small debug tasks (total: 30 minutes)
→ ✓ All pass (under duration limit)

User B submits 2 long tasks (total: 200 minutes)
→ ✓ First 2 pass
→ ✗ Third request blocked (duration limit exceeded + reached request limit)

After 24 hours: limits reset
```

#### Rate Limit Response

When rate limited, you'll receive detailed feedback:
```json
{
  "error": "Rate limit exceeded",
  "message": "Rate limit exceeded:\n  • Cumulative duration: 185.3 / 180 minutes (EXCEEDED)\n  • Request count: 3 / 3 (EXCEEDED)\n  • Time window: 24 hours\n  • Retry after: 2025-12-09T10:30:45"
}
```

#### Successful Submission Response

After successful submission, you'll receive remaining quota information:
```json
{
  "status": "accepted",
  "job_id": "job_abc123def456",
  "rate_limit_info": {
    "limit_mode": "both",
    "usage": {
      "duration": {
        "used_minutes": 45.2,
        "remaining_minutes": 134.8,
        "limit_minutes": 180
      },
      "requests": {
        "used": 2,
        "remaining": 1,
        "limit": 3
      }
    }
  }
}
```

#### Data Persistence

Rate limit data is persisted to disk (`dumps_public_service/ip_rate_limit_data.json`), which means:
- ✓ Limits survive server restarts
- ✓ No way to bypass by restarting server
- ✓ Fair enforcement across all users

#### Automatic Cleanup

The server automatically cleans up old data:
- Job directories older than 7 days are deleted (runs every 24 hours)
- Rate limit data within 24-hour window is preserved
- Keeps disk usage under control

#### Contact for Higher Limits

Public server uses conservative limits. For higher limits:
- Email: jlini@cse.ust.hk
- We can provide dedicated evaluation channels for major users (free of charge)

---

## Version Compatibility

### Current Versions
- **Server Version**: 1.1
- **Client Version**: 1.1
- **Supported Client Versions**: 1.0, 1.1

### Version History

**v1.1 (Current)**
- Added `--provider` parameter for model provider selection
- Supported providers: `unified` (default), `openai_stateful_responses`
- Automatic `manage_context` tool disabling for stateful providers
- Backward compatible with v1.0 clients (provider defaults to `unified`)

**v1.0**
- Initial release
- Single provider mode (unified)
- All core features (public/private mode, rate limiting, task management)

### Compatibility Notes

**v1.0 clients → v1.1 server:**
- ✓ Fully compatible
- Provider automatically defaults to `unified`
- All v1.0 features work as expected

**v1.1 clients → v1.0 server:**
- ✗ Not supported
- Server will reject v1.1 client with version error
- Update server to v1.1 or downgrade client to v1.0

**Checking versions:**
```bash
# Client version (defined at top of eval_client.py)
grep "CLIENT_VERSION" eval_client.py

# Server version (shown in startup output)
python eval_server.py 8080 8081
```

---

## Get Help

For detailed help on any command:

```bash
# Main help
python eval_client.py --help

# Command-specific help
python eval_client.py run --help
python eval_client.py status --help
python eval_client.py cancel --help
python eval_client.py check --help
```

If you encounter any issues, please contact us:
- Email: jlini@cse.ust.hk
- We can help test your model with provided API endpoint
- We can set up dedicated evaluation channels for major users

---

## Server Setup (For Server Administrators)

This section is mainly for developers running the server side. Skip this if you just want to use the service as a client.

### Prerequisites

Server requires full Toolathlon environment:

```bash
# Install dependencies
bash global_preparation/install_env_minimal.sh true

# Deploy local services (Canvas, email, etc.)
bash global_preparation/deploy_containers.sh true

# Install server dependencies
pip install fastapi uvicorn websockets
# Or use uv
uv add fastapi uvicorn websockets
```

### Start Server

```bash
python eval_server.py <server_port> <ws_proxy_port> <max_submissions_per_ip> <max_workers> <max_duration_minutes>
```

**Parameters:**
- `server_port` - Main server port (default: 8080)
- `ws_proxy_port` - WebSocket proxy port for private mode (default: 8081)
- `max_submissions_per_ip` - Max requests per IP per 24h (default: 3, use -1 for unlimited)
- `max_workers` - Max parallel workers per task (default: 10)
- `max_duration_minutes` - Max cumulative execution time per IP per 24h in minutes (default: 180, use -1 for unlimited)

**Examples:**

```bash
# Default: Dual limit (180 min duration + 3 requests per IP per 24h)
python eval_server.py 8080 8081 3 10 180

# Duration-only limit: 300 minutes, unlimited requests
python eval_server.py 8080 8081 -1 10 300

# Count-only limit: 10 requests, unlimited duration
python eval_server.py 8080 8081 10 10 -1

# Completely unlimited (no rate limiting)
python eval_server.py 8080 8081 -1 10 -1

# Custom dual limit: 5 requests + 240 minutes
python eval_server.py 8080 8081 5 10 240
```

**Server output:**

Dual limit mode (default):
```
============================================================
Toolathlon Remote Evaluation Server
============================================================
Server Version: 1.1
Supported Client Versions: 1.0, 1.1
Server Port: 8080
WebSocket Proxy Port: 8081 (for private mode)
Rate limiting: Dual limit (duration: 180 minutes per 24 hours, count: 3 per 24 hours)
Max workers per task: 10
Timeout: 240 minutes
Output directory: ./dumps_public_service
============================================================
No existing rate limit data file found, starting fresh
✓ WebSocket proxy started (PID: 12345)
  Log: ./dumps_public_service/ws_proxy.log
============================================================
[Server] Started background cleanup task (runs every 24 hours)
```

Duration-only mode:
```
============================================================
Toolathlon Remote Evaluation Server
============================================================
Server Version: 1.1
Supported Client Versions: 1.0, 1.1
Server Port: 8080
WebSocket Proxy Port: 8081 (for private mode)
Rate limiting: Duration limit only: 300 minutes per 24 hours
Max workers per task: 10
Timeout: 240 minutes
Output directory: ./dumps_public_service
============================================================
Loaded rate limit data: 5 IPs, 42 total records
✓ WebSocket proxy started (PID: 12345)
  Log: ./dumps_public_service/ws_proxy.log
============================================================
[Server] Started background cleanup task (runs every 24 hours)
```

Unlimited mode:
```
============================================================
Toolathlon Remote Evaluation Server
============================================================
Server Version: 1.1
Supported Client Versions: 1.0, 1.1
Server Port: 8080
WebSocket Proxy Port: 8081 (for private mode)
Rate limiting: No rate limiting
Max workers per task: 10
Timeout: 240 minutes
Output directory: ./dumps_public_service
============================================================
✓ WebSocket proxy started (PID: 12345)
  Log: ./dumps_public_service/ws_proxy.log
============================================================
[Server] Started background cleanup task (runs every 24 hours)
```

### Server Configuration

**Core Settings:**
- **Timeout:** 240 minutes (4 hours) per task
- **Concurrent tasks:** 1 task at a time (single-job queue to ensure resource availability)
- **Max workers:** Configurable per task (default: 10)
- **Output directory:** `./dumps_public_service/` (hardcoded in `eval_server.py`)

**Rate Limiting:**
- **Dual-limit system:** Duration threshold + request count limit
- **Time window:** 24 hours (configurable via `RATE_LIMIT_HOURS` in code)
- **Default limits:** 180 minutes cumulative duration + 3 requests
- **Persistence:** Rate limit data saved to `dumps_public_service/ip_rate_limit_data.json`
- **Survives restarts:** Data persists across server restarts

**Automatic Cleanup:**
- **Frequency:** Every 24 hours
- **Cleanup rule:** Delete job directories older than 7 days (based on last modification time)
- **Protected files:** `ip_rate_limit_data.json` is never deleted
- **Background task:** Starts automatically on server startup
- **Purpose:** Prevents disk usage from growing indefinitely

**Job Tracking:**
Each job submission records:
- Job ID and client IP
- Submission timestamp
- Completion timestamp
- Execution duration
- All stored in persistent rate limit data file

### Server Management

**Graceful shutdown:**
Press `Ctrl+C` to trigger graceful shutdown. The server will:
- Stop accepting new tasks
- Kill running evaluation processes
- Clean up Docker containers
- Close WebSocket proxy

**View server logs:**
```bash
# Main server log (stdout)
# Shown in terminal where server is running

# WebSocket proxy log
tail -f ./dumps_public_service/ws_proxy.log

# Individual job logs
tail -f ./dumps_public_service/<job_id>/server_stdout.log
```
