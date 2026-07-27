# record start time
start_time=$(date +%s)
echo "Start time: $(date)"

poste_configure_dovecot=${1:-true}
echo "============================================================================================="
echo "poste_configure_dovecot: $poste_configure_dovecot"
echo "For some Linux distributions, you need to configure Dovecot to allow plaintext auth."
echo "If you are not sure, please set to true."
echo "Our experience: Ubuntu 24.04 should set this as true, but AlmaLinux should set this as false."
echo "============================================================================================="

sleep 5

# ---------------------------------------------------------------------------
# Container runtime + instance suffix (read once, used throughout).
#   - podman_or_docker comes from configs/global_configs.py
#   - instance_suffix comes from configs/ports_config.yaml
# ${CTR} is used for all generic container CLI calls (prune/pull/inspect/
# exec) so this script works under both docker and podman.  The explicit
# stop/rm section below keeps its own docker/podman branch because podman
# additionally needs `pod rm`.
# ---------------------------------------------------------------------------
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)" 2>/dev/null || echo "docker")
CTR="$podman_or_docker"
instance_suffix=$(uv run python -c "
import yaml
try:
    with open('configs/ports_config.yaml', 'r') as f:
        config = yaml.safe_load(f) or {}
        print(config.get('instance_suffix', '') or '')
except Exception:
    print('')
" 2>/dev/null || echo "")
echo "Container runtime: $CTR    instance_suffix: '${instance_suffix}'"

# ---------------------------------------------------------------------------
# Reclaim disk that previous failed-deploy attempts may have leaked.
#
# Every time a shared-infra container crashes and setup.sh restarts it, the
# runtime creates a fresh anonymous volume for the new container.  Old
# volumes left behind ("dangling") accumulate to hundreds of GB across
# thousands of restarts and eventually fill the disk, at which point
# subsequent deploys fail with "No space left on device" from inside
# mysqld / canvas postgres.  Prune at deploy start so we begin with the
# largest possible free disk.
# ---------------------------------------------------------------------------
echo "============================================================================================="
echo "Disk-reclaim sweep before deploy ..."
echo "============================================================================================="
df -h / | awk 'NR==1 || /\//' | head -2
$CTR volume prune -f 2>&1 | grep -E "reclaimed|^[a-f0-9]{6,}" | tail -3 || true
$CTR container prune -f --filter "until=24h" 2>&1 | grep -E "reclaimed|^[a-f0-9]{6,}" | tail -3 || true
$CTR image prune -f 2>&1 | grep -E "reclaimed" | tail -1 || true
df -h / | awk '/\//' | head -1
echo "============================================================================================="
echo ""

# ---------------------------------------------------------------------------
# Refresh the host's image cache for images referenced by the k8s tasks.
# Per-task preprocess scripts then use the shared platform-scoped loader to
# stream these cached images into their Kind nodes offline — no Docker Hub
# round trip per preprocess → no rate-limit issues under repeated runs.
#
# Best-effort: anonymous Docker Hub allows ~100 pulls / 6h per IP, so a
# refresh sweep that exceeds the quota will start failing midway.  Each pull
# is run with a short timeout, return-codes are ignored, and we continue on
# failure.  Even partial success is a win — anything already cached is enough
# for that image's pre-load step in preprocess.
# ---------------------------------------------------------------------------
echo "============================================================================================="
echo "Refreshing image cache for k8s task images (best-effort, never fails the deploy) ..."
echo "============================================================================================="
K8S_TASK_IMAGES=(
    # k8s-mysql
    mysql:8.4
    nginx:1.14
    # k8s-deployment-cleanup
    nginx:1.20-alpine
    # k8s-redis-helm-upgrade (distractor pods)
    oliver006/redis_exporter:v1.45.0
    nginx:1.21-alpine
    # k8s-safety-audit
    alpine:3.20
    busybox:1.36
    nginxinc/nginx-unprivileged:1.25-alpine
    prom/prometheus:v2.52.0
    python:3.12-alpine
    redis:7.2
    # k8s-pr-preview-testing (preview.yaml from feature/pr-123 branch)
    nginx:1.25-alpine
)
_pulled=0
_skipped=0
_failed=0
for _img in "${K8S_TASK_IMAGES[@]}"; do
    # 30s timeout per pull — if Docker Hub is rate-limiting we'll fail
    # fast and move on.  --quiet keeps output minimal in steady state.
    if timeout 30 $CTR pull --quiet "$_img" >/dev/null 2>&1; then
        _pulled=$(( _pulled + 1 ))
    else
        if $CTR image inspect "$_img" >/dev/null 2>&1; then
            _skipped=$(( _skipped + 1 ))   # have a stale copy, fine
        else
            _failed=$(( _failed + 1 ))     # don't have it; next preprocess will pull
        fi
    fi
done
echo "  pulled/refreshed: $_pulled    not refreshed but cached: $_skipped    missing: $_failed    (total: ${#K8S_TASK_IMAGES[@]})"
echo "============================================================================================="
echo ""

# ---------------------------------------------------------------------------
# Per-service ports.  apply_port_numbers.py rewrites these via its bounded
# regex (`(?<![0-9])<old>(?![0-9])`) on every run, so both this file's named
# variables and the REQUIRED_PORTS array stay in sync with ports_config.yaml.
# ---------------------------------------------------------------------------
CANVAS_HTTP_PORT=10001
CANVAS_HTTPS_PORT=20001
POSTE_WEB_PORT=10005
POSTE_SMTP_PORT=2525
POSTE_IMAP_PORT=1143
POSTE_SUB_PORT=1587
WOO_PORT=10003
K8S_PR_PORT=30123
K8S_MYSQL_PORT=30124
WEB_TASK_PORT=30137

REQUIRED_PORTS=($CANVAS_HTTP_PORT $CANVAS_HTTPS_PORT $POSTE_WEB_PORT $POSTE_SMTP_PORT $POSTE_IMAP_PORT $POSTE_SUB_PORT $WOO_PORT $K8S_PR_PORT $K8S_MYSQL_PORT $WEB_TASK_PORT)

# ---------------------------------------------------------------------------
# Retry / readiness tunables
# ---------------------------------------------------------------------------
MAX_DEPLOY_ATTEMPTS=2          # how many times to (re)run the full setup
READINESS_TIMEOUT_SECONDS=1800 # 30 min: matches the outer asyncio cap in _deploy_infrastructure
PROBE_INTERVAL_SECONDS=5

KIND_CLUSTER_NAME="cluster${instance_suffix}1-control-plane"

# ---------------------------------------------------------------------------
# Readiness probes — each returns 0 if the service is up and serving.
# Probe semantics chosen to match what real clients hit:
#   - Canvas Rails API actually responding (not just the TCP port being open).
#   - Poste IMAP/SMTP/SMTP-submission speaking their protocol banners.
#   - WooCommerce serving HTTP (the storefront 302s to login when ready).
#   - Kind cluster's control-plane node reporting Ready via kubectl.
# ---------------------------------------------------------------------------
canvas_ready() {
    # Canvas Rails API returns 401 with a JSON body when alive but unauthed.
    # Don't use curl -f (it would treat 401 as failure); just check the body.
    curl -s --max-time 5 "http://localhost:$CANVAS_HTTP_PORT/api/v1/accounts" 2>/dev/null \
        | grep -q '"status"\|"errors"'
}
poste_web_ready() {
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:$POSTE_WEB_PORT/")
    [ "$code" = "302" ] || [ "$code" = "200" ]
}
poste_imap_ready() {
    (echo "a1 CAPABILITY"; sleep 0.2; echo "a2 LOGOUT") \
        | timeout 5 nc -w 3 localhost $POSTE_IMAP_PORT 2>/dev/null \
        | grep -q 'IMAP4rev1'
}
poste_smtp_ready_at() {  # arg: port
    (echo "EHLO healthcheck"; sleep 0.2; echo "QUIT") \
        | timeout 5 nc -w 3 localhost $1 2>/dev/null \
        | grep -q 'ESMTP'
}
woo_ready() {
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:$WOO_PORT/")
    [ "$code" = "302" ] || [ "$code" = "200" ]
}
kind_ready() {
    $CTR exec "$KIND_CLUSTER_NAME" \
        kubectl --kubeconfig=/etc/kubernetes/admin.conf get nodes --no-headers 2>/dev/null \
        | grep -q ' Ready '
}

probe_all() {
    canvas_ready          || { echo "  ✗ canvas not ready (:$CANVAS_HTTP_PORT)";        return 1; }
    poste_web_ready       || { echo "  ✗ poste web not ready (:$POSTE_WEB_PORT)";       return 1; }
    poste_imap_ready      || { echo "  ✗ poste imap not ready (:$POSTE_IMAP_PORT)";     return 1; }
    poste_smtp_ready_at $POSTE_SMTP_PORT || { echo "  ✗ poste smtp not ready (:$POSTE_SMTP_PORT)"; return 1; }
    poste_smtp_ready_at $POSTE_SUB_PORT  || { echo "  ✗ poste submission not ready (:$POSTE_SUB_PORT)"; return 1; }
    woo_ready             || { echo "  ✗ woocommerce not ready (:$WOO_PORT)";           return 1; }
    kind_ready            || { echo "  ✗ kind cluster not ready ($KIND_CLUSTER_NAME)";  return 1; }
    return 0
}

wait_for_all_ready() {
    local timeout=$1
    local deadline=$(( $(date +%s) + timeout ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if probe_all >/dev/null 2>&1; then
            echo "  ✓ all infra services ready"
            return 0
        fi
        local left=$(( deadline - $(date +%s) ))
        echo "  …waiting for services to be ready (${left}s left)"
        sleep $PROBE_INTERVAL_SECONDS
    done
    echo "  TIMEOUT — last failing probes:"
    probe_all || true
    return 1
}

# ---------------------------------------------------------------------------
# Run the actual setup steps.  Each component's setup.sh start is idempotent
# (it stops any existing instance first), so calling this in a retry loop is
# safe.  The four components touch disjoint container names / ports /
# networks, so they're also safe to run concurrently — each one's internal
# stop-then-start cleanup still applies, just in parallel.  Per-component
# output is captured to its own log file so a slow component (e.g. Canvas
# first-boot) doesn't bury the others' progress; logs are replayed tagged
# after all four finish.
# ---------------------------------------------------------------------------
run_setup() {
    local logdir
    logdir=$(mktemp -d -t toolathlon-deploy-XXXXXX)
    echo "  parallel setup logs: $logdir  (tail -f \$logdir/<component>.log for live progress)"

    (
        bash deployment/k8s/scripts/setup.sh > "$logdir/k8s.log" 2>&1
        echo $? > "$logdir/k8s.rc"
    ) &
    local pid_k8s=$!

    (
        bash deployment/canvas/scripts/setup.sh > "$logdir/canvas.log" 2>&1 # port $CANVAS_HTTP_PORT $CANVAS_HTTPS_PORT
        echo $? > "$logdir/canvas.rc"
    ) &
    local pid_canvas=$!

    (
        bash deployment/poste/scripts/setup.sh start $poste_configure_dovecot > "$logdir/poste.log" 2>&1 # port $POSTE_WEB_PORT $POSTE_SMTP_PORT $POSTE_IMAP_PORT $POSTE_SUB_PORT
        echo $? > "$logdir/poste.rc"
    ) &
    local pid_poste=$!

    (
        bash deployment/woocommerce/scripts/setup.sh start 81 20 > "$logdir/woo.log" 2>&1 # port $WOO_PORT
        echo $? > "$logdir/woo.rc"
    ) &
    local pid_woo=$!

    echo "  launched in parallel: k8s=$pid_k8s canvas=$pid_canvas poste=$pid_poste woo=$pid_woo"

    wait "$pid_k8s" "$pid_canvas" "$pid_poste" "$pid_woo"

    local c rc any_fail=0
    for c in k8s canvas poste woo; do
        rc=$(cat "$logdir/$c.rc" 2>/dev/null || echo "?")
        [ "$rc" != "0" ] && any_fail=1
        echo ""
        echo "----- [$c] setup.sh exit=$rc -----"
        sed "s|^|[$c] |" "$logdir/$c.log" 2>/dev/null || true
    done

    # Keep $logdir on disk for post-mortem (logs are tiny).  Each new deploy
    # makes a fresh dir; old ones can be reaped manually if needed.
    echo ""
    echo "  parallel setup logs preserved at: $logdir"

    # Propagate setup.sh failure: tells the retry loop to skip the 30-min
    # readiness wait and either rerun setup or fail fast.  Without this, a
    # `kind create` failure would stay invisible until readiness times out.
    return $any_fail
}

# ---------------------------------------------------------------------------
# Explicit pre-stop cleanup (runtime-aware) — runs ONCE before the retry
# loop.  Each setup.sh start is itself idempotent, but this extra sweep is a
# safety net against leftover containers/networks (e.g. a previous deploy
# that was killed mid-flight) that could otherwise cause name/network/port
# conflicts on the next start.  podman additionally needs `pod rm`.
# ---------------------------------------------------------------------------
echo "============================================================================================="
echo "Stopping existing Docker/Podman services cleanly..."
echo "============================================================================================="

bash deployment/poste/scripts/setup.sh stop "$poste_configure_dovecot" || true
bash deployment/woocommerce/scripts/setup.sh stop || true
bash deployment/canvas/scripts/setup.sh stop || true

if [ "$podman_or_docker" = "docker" ]; then
    docker rm -f "poste${instance_suffix}" "woo-wp${instance_suffix}" "woo-db${instance_suffix}" "canvas-docker${instance_suffix}" 2>/dev/null || true
    docker network rm "woo-net${instance_suffix}" 2>/dev/null || true
elif [ "$podman_or_docker" = "podman" ]; then
    podman rm -f "poste${instance_suffix}" "woo-wp${instance_suffix}" "woo-db${instance_suffix}" "canvas-docker${instance_suffix}" 2>/dev/null || true
    podman network rm "woo-net${instance_suffix}" 2>/dev/null || true
    podman pod rm -f "woo-pod${instance_suffix}" 2>/dev/null || true
fi

sleep 2

# ---------------------------------------------------------------------------
# Kill processes occupying required ports.  Skip runtime-managed processes
# (docker-proxy / podman) — those are torn down by the container cleanup
# above / each setup.sh's own start, and force-killing them can leave the
# runtime's port bookkeeping inconsistent.  Only non-runtime squatters get
# killed here.
# ---------------------------------------------------------------------------
echo "============================================================================================="
echo "Checking and killing processes on required ports..."
echo "============================================================================================="

for port in "${REQUIRED_PORTS[@]}"; do
    if lsof -i :$port -t >/dev/null 2>&1; then
        echo "Port $port is in use. Checking process(es)..."
        pids=$(lsof -i :$port -t)

        for pid in $pids; do
            process_name=$(ps -p "$pid" -o comm= 2>/dev/null || true)
            process_args=$(ps -p "$pid" -o args= 2>/dev/null || true)

            case "$process_name:$process_args" in
                *docker-proxy*|*com.docker.backend*|*podman*)
                    echo "  Skipping Docker/Podman-managed process PID $pid ($process_name). Clean containers instead."
                    ;;
                *)
                    echo "  Killing non-Docker PID $pid on port $port ($process_name)"
                    kill -9 "$pid" 2>/dev/null || true
                    ;;
            esac
        done

        sleep 1

        if lsof -i :$port -t >/dev/null 2>&1; then
            echo "  Warning: port $port is still in use after cleanup"
            lsof -i :$port || true
        else
            echo "  Port $port cleared"
        fi
    else
        echo "Port $port is free"
    fi
done

echo "All required ports checked and cleared"
echo "============================================================================================="
echo ""

# ---------------------------------------------------------------------------
# Retry loop: setup (parallel) → wait for readiness → on timeout/failure,
# redeploy from scratch.
# ---------------------------------------------------------------------------
attempt=1
while [ $attempt -le $MAX_DEPLOY_ATTEMPTS ]; do
    echo "============================================================================================="
    echo "Deploy attempt $attempt of $MAX_DEPLOY_ATTEMPTS (cluster=$KIND_CLUSTER_NAME)"
    echo "============================================================================================="

    # If any of the four setup.sh scripts already reported failure, skip the
    # readiness wait — there's no point burning 30 min probing for a service
    # we know didn't start.  Go straight to retry (or final-fail).
    if run_setup; then
        echo ""
        echo "Waiting up to ${READINESS_TIMEOUT_SECONDS}s for all services to be ready..."
        if wait_for_all_ready $READINESS_TIMEOUT_SECONDS; then
            echo "Deploy attempt $attempt succeeded."
            break
        fi
        retry_reason="services not ready in time"
    else
        retry_reason="one or more setup.sh scripts reported failure"
    fi

    if [ $attempt -ge $MAX_DEPLOY_ATTEMPTS ]; then
        echo "ERROR: $retry_reason after $MAX_DEPLOY_ATTEMPTS attempts. Giving up."
        echo "Exit time: $(date)"
        echo "Total time: $(($(date +%s) - start_time)) seconds"
        exit 1
    fi

    echo ""
    echo "============================================================================================="
    echo "$retry_reason on attempt $attempt — re-running deploy from the beginning."
    echo "============================================================================================="
    attempt=$((attempt + 1))
done

# we also use $K8S_PR_PORT, $K8S_MYSQL_PORT ports in two of the k8s tasks
# we also use $WEB_TASK_PORT for a web task to deploy a web page locally

# record exit time
echo "Exit time: $(date)"

# record total time
echo "Total time: $(($(date +%s) - start_time)) seconds"
