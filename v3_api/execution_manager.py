"""In-memory state manager for v3 task executions.

Owns:
  * ``executions``: every active task execution, keyed by execution_id
  * ``lock_owner_by_key``: per-endpoint locks on ``task:{tid}`` and
    ``conflict:{group_id}``, mapping each lock key to the owning execution_id
  * ``manager_lock``: serialises admission decisions (capacity + lock check
    + reservation) so concurrent ``/start`` requests can't race through a
    stale status check
  * ``infra_lock``: separate lock that serialises shared-infrastructure
    health checks and (re)deploys.  Never held simultaneously with
    ``manager_lock`` so a slow deploy doesn't freeze new admissions on
    other healthy infra.
  * The idle/lifetime reaper task.

This module deliberately does no container work — see ``container_mgr``
for that.  Manager methods return outcome enums; the router maps them to
HTTP responses.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import ToolDef


def log(msg: str) -> None:
    local_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    utc_time = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{local_time}][UTC {utc_time}] [v3] {msg}", flush=True)


# ── Conflict groups ──────────────────────────────────────────────────
#
# Tasks listed in the same group share an external account / resource and
# must not run concurrently *on the same endpoint*.  These are endpoint-
# local; if multiple endpoints share a truly global external resource, the
# group needs a distributed lock backend (not implemented in v1 of v3).

TASK_CONFLICT_GROUPS: Dict[str, List[str]] = {
    "calendar_course": [
        "set-conf-cr-ddl",
        "student-interview",
    ],
    "hf_dataset": [
        "huggingface-upload",
        "dataset-license-issue",
    ],
    "woocommerce": [
        "woocommerce-customer-survey",
        "woocommerce-product-recall",
    ],
    "canvas_courses": [
        "canvas-submit-late-work",
        "canvas-do-quiz",
    ],
}

# Reverse index: task_id -> group_id (built once at import).
_TASK_TO_GROUP: Dict[str, str] = {}
for _gid, _tasks in TASK_CONFLICT_GROUPS.items():
    for _t in _tasks:
        _TASK_TO_GROUP[_t] = _gid


def conflict_group_for(task_id: str) -> Optional[str]:
    return _TASK_TO_GROUP.get(task_id)


def lock_keys_for(task_id: str) -> List[str]:
    """Per-execution lock keys.  Always includes ``task:{task_id}``; adds
    ``conflict:{group_id}`` when the task is in a configured conflict group.
    """
    keys = [f"task:{task_id}"]
    group = conflict_group_for(task_id)
    if group is not None:
        keys.append(f"conflict:{group}")
    return keys


# ── Configuration knobs ──────────────────────────────────────────────

MAX_ACTIVE_EXECUTIONS = int(os.environ.get("TOOLATHLON_V3_MAX_ACTIVE_EXECUTIONS", "30"))
TASK_LIFETIME_SECONDS = int(os.environ.get("TOOLATHLON_V3_TASK_LIFETIME_SECONDS", "7200"))    # 120 min after ready
SETUP_TIMEOUT_SECONDS = int(os.environ.get("TOOLATHLON_V3_SETUP_TIMEOUT_SECONDS", "1800"))    # 30 min from /start
IDLE_TIMEOUT_SECONDS = int(os.environ.get("TOOLATHLON_V3_IDLE_TIMEOUT_SECONDS", "1200"))      # 20 min since last activity
REAPER_INTERVAL_SECONDS = int(os.environ.get("TOOLATHLON_V3_REAPER_INTERVAL_SECONDS", "60"))
SKIP_DEPLOY = os.environ.get("TOOLATHLON_V3_SKIP_DEPLOY", "").lower() in ("1", "true", "yes")
INFRA_HEALTH_TTL_SECONDS = float(os.environ.get("TOOLATHLON_V3_INFRA_HEALTH_TTL_SECONDS", "30"))

# Periodic full reset (deploy_containers.sh re-run) cadence.  The
# reaper drives a two-phase reset:
#   Phase 1 — DRAIN: once this many seconds have elapsed since the last
#   successful reset, ``deploy_status`` flips to ``"draining"``.
#   Admission immediately starts rejecting new tasks with INFRA_DRAINING;
#   in-flight tasks continue undisturbed.
#   Phase 2 — RESET: once the executions dict drains to empty (in-flight
#   tasks finish naturally OR get reaped by setup/lifetime/idle timers),
#   ``deploy_status`` flips to ``"repairing"`` and ``deploy_containers.sh``
#   runs.  On success ``last_full_reset_at`` is re-stamped and the clock
#   restarts.
# This guarantees a reset cadence of (interval + worst-case drain
# duration), bounded by the lifetime timer (TASK_LIFETIME_SECONDS).
# Set to ``0`` to disable periodic resets entirely.
PERIODIC_RESET_INTERVAL_SECONDS = int(
    os.environ.get("TOOLATHLON_V3_PERIODIC_RESET_INTERVAL_SECONDS", "21600")
)  # 6h default
INFRA_RETRY_AFTER_SECONDS = float(os.environ.get("TOOLATHLON_V3_INFRA_RETRY_AFTER_SECONDS", "30"))


# ── State types ──────────────────────────────────────────────────────

@dataclass
class ExecutionState:
    """One task execution.  Lifecycle:

        starting -> ready -> graded/cleaned
        starting -> (setup fail / cancellation) -> cleaned
        ready    -> (DELETE / watchdog / idle reap / lifetime reap) -> cleaned

    Every cleanup path runs ``manager.cleanup_execution`` exactly once, which
    drops ``manager.executions[execution_id]``, releases every key in
    ``lock_keys``, and stops the container.
    """
    execution_id: str
    task_id: str
    container_name: str
    gateway_port: int
    gateway_url: str
    output_folder: str
    task_stash_dir: Optional[str] = None  # host-side stash of withheld preprocess/eval/groundtruth dirs
    lock_keys: List[str] = field(default_factory=list)
    status: str = "starting"                # starting | ready | grading | stopping
    setup_status: str = "starting"          # starting | ready
    setup_phase: str = "container_start"
    tools: List[ToolDef] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    ready_at: Optional[float] = None
    last_activity_at: float = field(default_factory=time.time)
    setup_task: Optional[asyncio.Task] = None
    watchdog_task: Optional[asyncio.Task] = None
    client_id: Optional[str] = None
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def deadline_at(self) -> float:
        """Absolute lifetime backstop.

        Before ready: ``created_at + SETUP_TIMEOUT_SECONDS``.
        After ready:  ``ready_at + TASK_LIFETIME_SECONDS``.
        """
        if self.ready_at is None:
            return self.created_at + SETUP_TIMEOUT_SECONDS
        return self.ready_at + TASK_LIFETIME_SECONDS

    def remaining_lifetime(self) -> float:
        return max(0.0, self.deadline_at() - time.time())


# ── Admission outcomes ───────────────────────────────────────────────

class AdmissionOutcome(str, Enum):
    ADMITTED = "admitted"
    CAPACITY_FULL = "capacity_full"
    TASK_BUSY = "task_busy"
    CONFLICT_GROUP_BUSY = "conflict_group_busy"
    INFRA_CHECKING = "infra_checking"
    INFRA_REPAIRING = "infra_repairing"
    INFRA_DRAINING = "infra_draining"        # 4h elapsed; finishing existing
                                              # tasks then doing a reset
    INFRA_FAILED = "infra_failed"
    INFRA_DISABLED_OR_UNKNOWN = "infra_disabled_or_unknown"


@dataclass
class AdmissionResult:
    outcome: AdmissionOutcome
    execution: Optional[ExecutionState] = None
    busy_keys: List[str] = field(default_factory=list)
    retry_after_s: float = 0.0
    deploy_status: Optional[str] = None
    last_infra_error: Optional[str] = None


# ── Manager singleton ────────────────────────────────────────────────

class ExecutionManager:
    """Singleton manager.  Constructed once by the launcher; the router
    delegates all state work to it.
    """

    def __init__(self) -> None:
        self.executions: Dict[str, ExecutionState] = {}
        self.lock_owner_by_key: Dict[str, str] = {}
        self.manager_lock = asyncio.Lock()
        self.infra_lock = asyncio.Lock()
        # Tunables that the launcher may override before the reaper starts.
        # The module-level constants serve only as default values (resolved
        # from env vars at import time).
        self.max_active_executions = MAX_ACTIVE_EXECUTIONS
        self.idle_timeout_seconds = IDLE_TIMEOUT_SECONDS
        self.reaper_task: Optional[asyncio.Task] = None
        # deploy status: "unknown" | "checking" | "repairing" | "ready" | "failed" | "disabled_debug"
        self.deploy_status: str = "disabled_debug" if SKIP_DEPLOY else "unknown"
        self.deploy_task: Optional[asyncio.Task] = None
        self.last_infra_check_at: Optional[float] = None
        self.last_infra_error: Optional[str] = None
        # Wall-clock time of the most recent successful deploy_containers.sh
        # completion (set by ``_run_background_repair`` on success).  Used by
        # the reaper to gate periodic resets — see PERIODIC_RESET_INTERVAL_SECONDS.
        self.last_full_reset_at: Optional[float] = None

    # ── Lifecycle ────────────────────────────────────────────────

    def start_reaper(self) -> None:
        if self.reaper_task is None or self.reaper_task.done():
            self.reaper_task = asyncio.create_task(self._reaper_loop())

    async def shutdown(self) -> None:
        """Cancel reaper + in-flight shared-infra repair + per-execution
        setup/watchdog tasks, then stop every active container.  Called by
        the launcher's shutdown hook so per-task containers don't leak when
        the server is SIGTERM'd.
        """
        if self.reaper_task is not None and not self.reaper_task.done():
            self.reaper_task.cancel()
            try:
                await self.reaper_task
            except asyncio.CancelledError:
                pass
            self.reaper_task = None

        # Cancel any in-flight shared-infra repair.  Don't wait for the
        # SIGKILL'd ``deploy_containers.sh`` subprocess to fully reap —
        # the asyncio task's CancelledError handling kills the proc.
        if self.deploy_task is not None and not self.deploy_task.done():
            self.deploy_task.cancel()
            try:
                await self.deploy_task
            except (asyncio.CancelledError, Exception):
                pass
            self.deploy_task = None

        # Cancel per-execution inflight tasks first; cleanup_execution
        # below will docker rm.
        for ex in list(self.executions.values()):
            for t in (ex.setup_task, ex.watchdog_task):
                if t is not None and not t.done():
                    t.cancel()

        for ex in list(self.executions.values()):
            try:
                await self.cleanup_execution(ex, reason="shutdown")
            except Exception as e:
                log(f"shutdown: cleanup_execution({ex.execution_id}) failed: {e!r}")

    # ── Cached state queries ─────────────────────────────────────

    def cached_infra_is_fresh(self) -> bool:
        if self.deploy_status != "ready" or self.last_infra_check_at is None:
            return False
        return (time.time() - self.last_infra_check_at) < INFRA_HEALTH_TTL_SECONDS

    def busy_locks_snapshot(self) -> Dict[str, str]:
        return dict(self.lock_owner_by_key)

    def active_count(self) -> int:
        return len(self.executions)

    def capacity_available(self) -> bool:
        return self.active_count() < self.max_active_executions

    # ── Admission ────────────────────────────────────────────────

    async def try_admit(
        self,
        task_id: str,
        container_name: str,
        gateway_port: int,
        gateway_url: str,
        output_folder: str,
        *,
        model_name: Optional[str],
        client_id: Optional[str],
        metadata: Dict[str, Any],
    ) -> AdmissionResult:
        """Atomically check capacity + locks and, if all green, register
        a fresh ExecutionState.  The caller is responsible for spawning the
        setup task on the returned execution.

        This does NOT call ``ensure_shared_infra_ready`` — the router runs
        that first (without holding ``manager_lock``) so a slow shared-infra
        repair never blocks unrelated admissions.
        """
        keys = lock_keys_for(task_id)
        async with self.manager_lock:
            # Re-verify deploy status under the lock.  ensure_shared_infra_ready
            # ran without manager_lock, so it could have transitioned by now.
            if self.deploy_status not in ("ready", "disabled_debug"):
                outcome = {
                    "checking":  AdmissionOutcome.INFRA_CHECKING,
                    "repairing": AdmissionOutcome.INFRA_REPAIRING,
                    "draining":  AdmissionOutcome.INFRA_DRAINING,
                    "failed":    AdmissionOutcome.INFRA_FAILED,
                    "unknown":   AdmissionOutcome.INFRA_DISABLED_OR_UNKNOWN,
                }.get(self.deploy_status, AdmissionOutcome.INFRA_DISABLED_OR_UNKNOWN)
                return AdmissionResult(
                    outcome=outcome,
                    retry_after_s=INFRA_RETRY_AFTER_SECONDS,
                    deploy_status=self.deploy_status,
                    last_infra_error=self.last_infra_error,
                )

            if not self.capacity_available():
                return AdmissionResult(
                    outcome=AdmissionOutcome.CAPACITY_FULL,
                    retry_after_s=10.0,
                )

            busy_keys = [k for k in keys if k in self.lock_owner_by_key]
            if busy_keys:
                task_busy = any(k.startswith("task:") for k in busy_keys)
                outcome = AdmissionOutcome.TASK_BUSY if task_busy else AdmissionOutcome.CONFLICT_GROUP_BUSY
                # Pick a sensible retry-after based on the youngest competing
                # execution's remaining lifetime.  Cheap heuristic; clients
                # will jitter on top.
                competitor_age = min(
                    (
                        time.time() - self.executions[self.lock_owner_by_key[k]].created_at
                        for k in busy_keys
                        if self.lock_owner_by_key.get(k) in self.executions
                    ),
                    default=10.0,
                )
                return AdmissionResult(
                    outcome=outcome,
                    busy_keys=busy_keys,
                    retry_after_s=max(5.0, 30.0 - competitor_age),
                )

            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            now = time.time()
            ex = ExecutionState(
                execution_id=execution_id,
                task_id=task_id,
                container_name=container_name,
                gateway_port=gateway_port,
                gateway_url=gateway_url,
                output_folder=output_folder,
                lock_keys=list(keys),
                created_at=now,
                last_activity_at=now,
                client_id=client_id,
                model_name=model_name,
                metadata=dict(metadata),
            )
            self.executions[execution_id] = ex
            for k in keys:
                self.lock_owner_by_key[k] = execution_id

            log(
                f"Admitted {execution_id} task={task_id} locks={keys} "
                f"active={self.active_count()}/{self.max_active_executions}"
            )
            return AdmissionResult(outcome=AdmissionOutcome.ADMITTED, execution=ex)

    # ── Cleanup ──────────────────────────────────────────────────

    async def cleanup_execution(self, execution: ExecutionState, *, reason: str) -> None:
        """Single converging cleanup path used by every terminal outcome.

        Does NOT cancel ``setup_task`` or ``watchdog_task`` — callers are
        expected to handle cancellation themselves (or, for the
        watchdog-driven path, the watchdog task is the caller and is about
        to exit anyway).  This keeps the lock window short.
        """
        async with self.manager_lock:
            existed = self.executions.pop(execution.execution_id, None) is not None
            if existed:
                for k in execution.lock_keys:
                    if self.lock_owner_by_key.get(k) == execution.execution_id:
                        self.lock_owner_by_key.pop(k, None)
                log(
                    f"Cleaned {execution.execution_id} task={execution.task_id} "
                    f"reason={reason} released_locks={execution.lock_keys} "
                    f"active={self.active_count()}/{self.max_active_executions}"
                )

        # Deregister from the GitHub admission gate.  Best-effort: any
        # IO or lock failure here is swallowed because the entry will
        # age out via the gate's STALE_CONCURRENT_SECONDS safety-net.
        try:
            from .github_admission import deregister_admission
            deregister_admission(execution.execution_id)
        except Exception as e:
            log(f"github_admission deregister for {execution.execution_id} failed: {e!r}")

        # Container teardown happens outside manager_lock — docker rm is slow.
        # Import lazily to avoid a circular dep.
        from .container_mgr import teardown_container
        await teardown_container(execution)

    # ── Activity / status helpers ────────────────────────────────

    def touch_activity(self, execution: ExecutionState) -> None:
        execution.last_activity_at = time.time()

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        return self.executions.get(execution_id)

    # ── Shared-infra readiness helper ─────────────────────────────

    async def ensure_shared_infra_ready(self, *, trigger_repair: bool) -> bool:
        """Authoritative readiness gate for ``/start`` (and observability for
        ``/health``).  Returns True if shared infra is healthy right now;
        returns False if a task start cannot be admitted right now.

        No HTTP request ever blocks on the slow path:
          * Cached-and-fresh → return True immediately, no lock.
          * Cache stale, fast probe healthy (~1 s) → return True.
          * Cache stale, fast probe finds breakage, ``trigger_repair=True``
            → schedule ``deploy_containers.sh`` as a background task and
            return False.  The originating caller bounces with 503 just
            like everyone else; the repair runs to completion in the
            background.  Subsequent callers detect the in-flight task via
            ``self.deploy_task`` and bounce too — no parallel deploys.
          * A repair is already in flight (``self.deploy_task`` not done)
            → return False without acquiring the lock.

        Steady-state /start latency: < 1 ms on the cached-fresh path, ~1 s
        when the cache TTL expires and the fast probe re-runs.  Never the
        full deploy time, even for the caller that triggered the repair.
        """
        if self.deploy_status == "disabled_debug":
            return True
        # If we're already in a non-ready transition state, the
        # admission gate will reject correctly; never overwrite that
        # state by running the routine probe.
        if self.deploy_status == "draining":
            return False
        if self.cached_infra_is_fresh():
            return True

        # Bounce if a background repair is already in flight.
        if self.deploy_task is not None and not self.deploy_task.done():
            return False
        # Bounce if a peer is currently inside the (short) probe critical
        # section.  Note that the lock is NOT held for the duration of a
        # repair — only for the probe + decision + task-spawn.
        if self.infra_lock.locked():
            return False

        async with self.infra_lock:
            # Re-check everything under the lock; a peer may have raced us.
            if self.deploy_status == "disabled_debug":
                return True
            if self.deploy_status == "draining":
                return False
            if self.cached_infra_is_fresh():
                return True
            if self.deploy_task is not None and not self.deploy_task.done():
                return False

            from .container_mgr import fast_shared_infra_health_check

            self.deploy_status = "checking"
            log("shared-infra: cache stale, running behavioral probe (probe_shared_infra.py)")
            healthy, err = await fast_shared_infra_health_check()
            if healthy:
                self.deploy_status = "ready"
                self.last_infra_error = None
                self.last_infra_check_at = time.time()
                log("shared-infra: probe healthy (deploy_containers.sh not needed)")
                return True

            if not trigger_repair:
                self.deploy_status = "failed"
                self.last_infra_error = err or "fast health probe failed"
                log(f"shared-infra: probe found breakage (repair disabled): {err}")
                return False

            # Probe found breakage and we're allowed to repair.  But if
            # there are active in-flight tasks, repairing right now would
            # rebuild the shared containers (deploy_containers.sh nukes
            # canvas-docker, woo-wp, poste) which invalidates every
            # per-user token / re-initializes every account → the agent's
            # currently-running tool calls suddenly start returning
            # ``canvas_health_check: error``, even though admission saw a
            # healthy probe.
            #
            # In that situation, defer the repair: mark status as
            # ``"failed"`` (admission rejects new tasks with INFRA_FAILED
            # + retry_after) and DON'T schedule the repair task.  Once
            # active tasks drain (naturally or via reaper), a subsequent
            # probe check will re-find the breakage with executions
            # empty and finally trigger the repair.  Worst case: the
            # in-flight tasks fail anyway from the original infra
            # breakage, but we don't compound the failure by rebuilding
            # underneath them.
            if self.executions:
                self.deploy_status = "failed"
                self.last_infra_error = err
                log(
                    f"shared-infra: probe found breakage but {len(self.executions)} "
                    f"active task(s) — DEFERRING repair until drain: {err}"
                )
                return False

            # No active tasks — safe to repair.  Schedule the slow
            # ``deploy_containers.sh`` as a background task; the status
            # flip + task assignment happens *inside* the lock so the
            # next caller (entering after we release) sees them both
            # atomically.
            self.deploy_status = "repairing"
            self.last_infra_error = err  # remember the probe's failure msg
            self.deploy_task = asyncio.create_task(self._run_background_repair())
            log(f"shared-infra: probe found breakage: {err}")
            log("shared-infra: triggering deploy_containers.sh in background")
            return False

    def trigger_initial_deploy(self) -> None:
        """Force a fresh ``deploy_containers.sh`` run at launcher startup.

        Used by ``eval_server_v3.py``'s startup hook to satisfy the
        operator-requested invariant that every service restart means a
        fresh infrastructure restart — no probe shortcut, even if the
        previous instance's containers happen to still be alive.  Bypasses
        ``ensure_shared_infra_ready``'s "probe first, repair if broken"
        decision tree and goes straight to scheduling the deploy.

        No-op when ``TOOLATHLON_V3_SKIP_DEPLOY`` is set; ``deploy_status``
        stays at ``"disabled_debug"`` and admissions proceed without the
        deploy gate.

        Synchronous: sets state + spawns the background deploy task and
        returns immediately, so the launcher's startup hook does not block
        uvicorn from binding the port while the (multi-minute) deploy
        runs.  Clients arriving in the meantime see ``deploy_status =
        "repairing"`` and bounce with a fast ``503 infra_repairing``.
        """
        if SKIP_DEPLOY:
            log("shared-infra: TOOLATHLON_V3_SKIP_DEPLOY set, skipping initial deploy")
            return

        self.deploy_status = "repairing"
        self.last_infra_error = None
        self.last_infra_check_at = None
        self.deploy_task = asyncio.create_task(self._run_background_repair())
        log("shared-infra: forcing fresh deploy_containers.sh at startup (no probe)")

    async def _run_background_repair(self) -> None:
        """Background-task entry point for shared-infra redeploy.

        Holds no lock for its duration; concurrent callers detect this is
        in flight via ``self.deploy_task``.  Updates ``deploy_status`` and
        ``last_infra_error`` according to outcome:
          * success → ``deploy_status = "ready"``, ``last_infra_error = None``
          * failure → ``deploy_status = "failed"``, ``last_infra_error`` set
          * cancelled (e.g. server shutdown) → ``deploy_status = "failed"``
        """
        from .container_mgr import (
            fast_shared_infra_health_check,
            run_shared_infra_deploy,
        )
        try:
            await run_shared_infra_deploy()
            ok_after, err_after = await fast_shared_infra_health_check()
            if not ok_after:
                raise RuntimeError(
                    f"shared infra still unhealthy after redeploy: {err_after}"
                )
            self.deploy_status = "ready"
            self.last_infra_error = None
            now = time.time()
            self.last_infra_check_at = now
            self.last_full_reset_at = now
            log("shared-infra repair complete (status=ready)")
        except asyncio.CancelledError:
            self.deploy_status = "failed"
            self.last_infra_error = "repair cancelled"
            log("shared-infra repair cancelled")
            raise
        except Exception as exc:
            self.deploy_status = "failed"
            self.last_infra_error = repr(exc)
            log(f"shared-infra repair FAILED: {exc!r}")

    # ── Reaper loop ──────────────────────────────────────────────

    async def _reaper_loop(self) -> None:
        """Background task that enforces:
          * setup_timeout (created_at -> ready), per execution — only while
            the execution is still in setup
          * lifetime (ready_at + TASK_LIFETIME_SECONDS), per ready execution
          * idle_timeout (last_activity_at), per ready execution — the idle
            clock starts only after setup completes, because preprocessing
            can take many minutes and shouldn't count against the client's
            activity budget.  ``last_activity_at`` is re-stamped to
            ``ready_at`` at the end of ``_run_setup`` so the budget begins
            cleanly from there.
        """
        try:
            while True:
                await asyncio.sleep(REAPER_INTERVAL_SECONDS)
                now = time.time()
                victims: List[tuple[ExecutionState, str]] = []

                for ex in list(self.executions.values()):
                    if ex.setup_status != "ready":
                        # Pre-ready: only the setup_timeout backstop applies.
                        # No idle check — preprocess time is not idle time.
                        if now - ex.created_at > SETUP_TIMEOUT_SECONDS:
                            victims.append((ex, f"setup exceeded {SETUP_TIMEOUT_SECONDS}s"))
                        continue

                    # Post-ready: both lifetime and idle apply.
                    if ex.ready_at is not None and (now - ex.ready_at) > TASK_LIFETIME_SECONDS:
                        victims.append((ex, f"lifetime exceeded {TASK_LIFETIME_SECONDS}s"))
                        continue
                    if (now - ex.last_activity_at) > self.idle_timeout_seconds:
                        victims.append((ex, f"idle for {(now - ex.last_activity_at) / 60:.1f} min"))

                for ex, reason in victims:
                    log(f"reaper: {ex.execution_id} ({reason}), auto-cleaning")
                    for t in (ex.setup_task, ex.watchdog_task):
                        if t is not None and not t.done():
                            t.cancel()
                    try:
                        await self.cleanup_execution(ex, reason=f"reaper:{reason}")
                    except Exception as e:
                        log(f"reaper: cleanup_execution({ex.execution_id}) failed: {e!r}")

                # ── Periodic full reset of shared infra ─────────────────
                # Re-run deploy_containers.sh after PERIODIC_RESET_INTERVAL_SECONDS
                # have elapsed since the last completion, but ONLY when no
                # tasks are admitted right now.  ``manager_lock`` makes the
                # check + status flip atomic w.r.t. admission, so a task
                # cannot slip in between the empty check and the deploy
                # starting.  If a task is in flight, we defer to the next
                # reaper tick that finds the dict empty again.
                if PERIODIC_RESET_INTERVAL_SECONDS > 0:
                    await self._maybe_periodic_reset(now)
        except asyncio.CancelledError:
            pass

    async def _maybe_periodic_reset(self, now: float) -> None:
        """Two-phase periodic reset:

          Phase 1 — DRAIN: once PERIODIC_RESET_INTERVAL_SECONDS has elapsed
          since the last successful reset, flip ``deploy_status`` to
          ``"draining"``.  Admission immediately starts rejecting new
          tasks with INFRA_DRAINING.  In-flight tasks continue running
          undisturbed.

          Phase 2 — RESET: once the executions dict drains to empty
          (either naturally, or because the reaper killed timed-out
          tasks), flip ``deploy_status`` to ``"repairing"`` and schedule
          ``_run_background_repair`` which runs deploy_containers.sh and
          re-probes.  On success it sets status back to ``"ready"`` and
          re-stamps ``last_full_reset_at`` — restarting the interval
          clock.
        """
        async with self.manager_lock:
            if self.deploy_task is not None and not self.deploy_task.done():
                return  # a repair (manual or periodic) is already in flight
            if self.last_full_reset_at is None:
                return  # no baseline yet — wait for initial deploy
            elapsed = now - self.last_full_reset_at

            # Phase 1: enter drain
            if self.deploy_status == "ready" and elapsed >= PERIODIC_RESET_INTERVAL_SECONDS:
                log(
                    f"periodic reset: {elapsed / 3600:.1f}h elapsed — "
                    f"entering DRAIN; {len(self.executions)} active task(s) "
                    f"must finish before reset runs"
                )
                self.deploy_status = "draining"
                self.last_infra_error = None

            # Phase 2: once drained, reset
            if self.deploy_status == "draining" and not self.executions:
                log(
                    f"periodic reset: drain complete (0 active tasks) — "
                    f"scheduling deploy_containers.sh"
                )
                self.deploy_status = "repairing"
                self.last_infra_check_at = None  # invalidate probe cache
                self.deploy_task = asyncio.create_task(self._run_background_repair())


# Module-level singleton.  The launcher constructs it once; the router
# imports this name.
manager = ExecutionManager()
