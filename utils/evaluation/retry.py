"""Grader-level retry helper for evaluation checks against eventually-consistent
external services.

This is "Layer 2" of the two-tier retry strategy used by Toolathlon graders:

  * **Layer 1** (in shared helpers like ``utils/app_specific/woocommerce/client.py``,
    ``utils/app_specific/canvas/api_client.py``, ``utils/app_specific/poste/ops.py``,
    ``utils/app_specific/notion/ops.py``) retries a single network call
    when the transport fails (ConnectionError / Timeout / HTTP 5xx / 429).

  * **Layer 2** (here) re-runs the WHOLE semantic check until it passes or
    the trial budget is exhausted.  This is what catches "agent wrote
    successfully but our read is too early" — i.e. eventual-consistency or
    propagation lag, where the API returns 200 OK but the *content* is
    still stale.

Layer 1 cannot solve propagation lag because there is no exception to
catch — the server happily returns 200 OK with stale data.

Conventions
-----------
- ``check_fn`` must be **idempotent** and **side-effect-free**.  It may be
  called many times.
- ``check_fn`` returns ``(ok: bool, err: Optional[str])`` matching the
  convention already used throughout ``tasks/finalpool/*/evaluation/``.
- On the first ``ok=True``, ``grade_with_retry`` returns immediately —
  there is no extra delay on the happy path.
- The default budget is intentionally tight (3 trials, 5s interval = ~10s
  of sleep + check times).  Layer 2 is a safety net for propagation lag,
  not a replacement for thinking about whether a check is racing.  If a
  task is observed to legitimately need a longer budget, bump
  ``max_attempts`` for that specific task — don't widen the default.
"""

import time
from typing import Callable, Optional, Tuple


# Tight defaults: 3 trials with a 5-second gap = ~10s of sleeping on
# failure (plus the time each check itself takes).  This caps the wall-
# clock overhead of a failing grade at roughly 15 seconds total for
# typical checks, while still giving a couple of retries to absorb the
# common case where a write hasn't propagated yet.
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_POLL_S = 5


def grade_with_retry(
    check_fn: Callable[[], Tuple[bool, Optional[str]]],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    poll_s: float = DEFAULT_POLL_S,
    sleep_budget_s: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """Poll ``check_fn`` until it passes, ``max_attempts`` is reached, or
    (optionally) ``sleep_budget_s`` of sleeping is exhausted.

    Args:
        check_fn: Callable returning ``(ok, err_msg)``.  Must be idempotent
            and side-effect free.  Layer 1 should already bound how long a
            single call can take.
        max_attempts: Maximum number of times ``check_fn`` will be called.
            Default 3 — i.e. 1 initial try + up to 2 retries.
        poll_s: Sleep duration between attempts.  Default 5s.
        sleep_budget_s: Optional secondary cap on total sleep time.  If
            set, whichever of ``max_attempts`` or ``sleep_budget_s`` fires
            first stops the loop.  Default ``None`` (no wall-clock cap).

    Returns:
        ``(True, None)`` on first successful check, or ``(False, last_err)``
        when the trial budget is exhausted.

    Examples:
        >>> def check():
        ...     return os.path.exists("/tmp/marker"), "marker not found"
        >>> ok, err = grade_with_retry(check)   # 3 attempts, 5s apart
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    slept = 0.0
    last_err: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            ok, err = check_fn()
        except Exception as exc:
            # A Layer-1-exhausted exception (e.g. ConnectionError after 3
            # attempts) lands here.  Absorb it so the Layer-2 loop keeps
            # going — the next poll may find the backend recovered.
            ok, err = False, f"check raised {type(exc).__name__}: {exc}"

        if ok:
            return True, None
        last_err = err

        # Don't sleep after the final attempt.
        if attempt >= max_attempts:
            break

        # Optional wall-clock cap (mostly unused; provided for per-task
        # overrides where the test wants a hard time bound rather than an
        # attempt count).
        if sleep_budget_s is not None and slept + poll_s > sleep_budget_s:
            break

        time.sleep(poll_s)
        slept += poll_s

    return False, last_err
