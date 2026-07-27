"""Toolathlon-side launch wrapper for arxiv-mcp-server.

Patches the upstream ``arxiv_mcp_server`` package in memory before
invoking its ``main()`` entrypoint.  The upstream code is pinned in the
toolathlon container image, but its handlers have two flakiness sources
we want to neutralise without forking / patching the venv:

  1. **Stateless arxiv.org flakiness** — every handler that hits arxiv
     (``handle_search``, ``handle_download``, ``handle_list_papers``)
     makes a single ``arxiv.Client().results(...)`` call with no retry
     and a bare ``except Exception``.  One transient network hiccup or
     rate-limit (arxiv enforces ~1 req per 3s per IP, and toolathlon
     can run multiple v3 instances concurrently against the same outbound
     IP) → the handler returns ``Error: ...`` text → the agent sees a
     failed tool call.  Other handlers' attempts a moment later (after
     the rate window clears) succeed — which is exactly the "same call,
     different result" behaviour the user observed.

  2. **Stateful error caching (download_paper only)** — once
     ``handle_download`` fails, the module-global
     ``conversion_statuses[paper_id]`` entry is left with
     ``status='error'`` and NEVER cleaned up.  Subsequent calls for the
     same ``paper_id`` short-circuit to the cached error without ever
     re-attempting the network — sticky failure for the rest of the MCP
     server process lifetime.

This wrapper installs a single shared async retry helper around the
three network-touching handlers, with growing backoff between
attempts (1s, 2s, 4s — 7s of cumulative wait, fits comfortably in the
60s client_session_timeout we configure in arxiv_local.yaml).  For
``handle_download`` specifically, every attempt first evicts any stale
``conversion_statuses[paper_id]`` entry whose status is ``"error"``,
so the retries actually re-hit the network instead of just re-returning
the cached failure.

``handle_read_paper`` is intentionally NOT wrapped — it touches only
the local filesystem, has no arxiv calls, and retrying it would never
help (the file either exists or doesn't).

After patching, the wrapper invokes ``arxiv_mcp_server.main()``
exactly as the ``arxiv-mcp-server`` console script would.

The agent sees a single tool call → single tool result; all retries
happen inside this process and are invisible to the calling agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Awaitable, Callable, Dict, List, Tuple

import mcp.types as types

import arxiv_mcp_server  # noqa: F401
import arxiv_mcp_server.tools.download as _dl
import arxiv_mcp_server.tools.list_papers as _lp
import arxiv_mcp_server.tools.search as _sr
import arxiv_mcp_server.server as _srv


logger = logging.getLogger("arxiv-mcp-wrapper")

# Backoff schedule between attempts (in seconds).  Length = ATTEMPTS - 1.
# 1, 2, 4 → 7s cumulative wait worst case + 3 × call duration.
RETRY_BACKOFFS: Tuple[float, ...] = (1.0, 2.0, 4.0)
ATTEMPTS = len(RETRY_BACKOFFS) + 1  # = 4 total attempts


def _result_is_error(result: List[types.TextContent]) -> bool:
    """Check if a handler's response indicates a failure that's worth
    retrying.  The upstream handlers use two error-return styles —
    both must be detected.

    Style 1 (handle_search, handle_list_papers):
        TextContent(text="Error: <message>")           — bare leading "Error:"

    Style 2 (handle_download, handle_read_paper):
        TextContent(text='{"status": "error", ...}')   — structured JSON

    We deliberately do NOT treat a "Paper {id} not found on arXiv"
    response as retryable — that's a deterministic 404 from arxiv, not
    a transient blip.  Same for "Paper not found in storage" from
    handle_read_paper.
    """
    if not result:
        return False
    text = ""
    for chunk in result:
        if isinstance(chunk, types.TextContent):
            text += chunk.text
    if not text:
        return False

    # Style 1: bare "Error: ..." prefix.  Retry — unless it's a
    # deterministic "not found" we already saw arxiv return.
    if text.lstrip().startswith("Error:"):
        if "not found on arXiv" in text or "not found in storage" in text:
            return False
        return True

    # Style 2: JSON object with status field
    text_stripped = text.strip()
    if text_stripped.startswith("{"):
        try:
            obj = json.loads(text_stripped)
        except Exception:
            return False
        if isinstance(obj, dict) and obj.get("status") == "error":
            msg = str(obj.get("message", ""))
            if "not found on arXiv" in msg or "not found in storage" in msg:
                return False
            return True

    return False


async def _with_retry(
    label: str,
    coro_factory: Callable[[], Awaitable[List[types.TextContent]]],
    *,
    pre_attempt_hook: Callable[[], None] = lambda: None,
) -> List[types.TextContent]:
    """Run ``coro_factory()`` up to ``ATTEMPTS`` times.

    A result that ``_result_is_error`` flags as retryable, or any
    exception that propagates, counts as a failure → wait and try
    again.  Returns the last attempt's result (success or final
    failure) when the budget is exhausted.

    ``pre_attempt_hook`` is invoked synchronously before each attempt,
    used by ``handle_download``'s wrapper to evict stale cached error
    entries.
    """
    last_result: List[types.TextContent] | None = None
    last_exception: BaseException | None = None

    for i in range(ATTEMPTS):
        if i > 0:
            await asyncio.sleep(RETRY_BACKOFFS[min(i - 1, len(RETRY_BACKOFFS) - 1)])
        try:
            pre_attempt_hook()
        except Exception as e:
            logger.warning("%s: pre_attempt_hook raised on attempt %d: %r", label, i + 1, e)
        try:
            last_result = await coro_factory()
            last_exception = None
        except BaseException as e:  # asyncio.CancelledError + everything else
            last_exception = e
            last_result = [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "message": f"{label} raised on attempt {i + 1}: {e!r}",
                    }),
                )
            ]
            # If the parent cancelled us, don't keep retrying.
            if isinstance(e, asyncio.CancelledError):
                raise
            continue

        if not _result_is_error(last_result):
            if i > 0:
                logger.info("%s: recovered on attempt %d", label, i + 1)
            return last_result

        logger.info(
            "%s: attempt %d/%d returned a retryable error, will retry",
            label, i + 1, ATTEMPTS,
        )

    logger.warning(
        "%s: exhausted %d attempts; returning the last response",
        label, ATTEMPTS,
    )
    return last_result if last_result is not None else [
        types.TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": f"{label} exhausted retries with no result",
            }),
        )
    ]


# ── handle_download wrapper ──────────────────────────────────────────
# Capture the upstream handler and the conversion_statuses dict in
# closure so we can re-invoke + evict on each attempt.

_orig_handle_download = _dl.handle_download


def _evict_stale_download_error(paper_id: str) -> None:
    """If ``conversion_statuses[paper_id]`` is currently in ``"error"``
    state, drop it so the next call genuinely retries instead of
    short-circuiting to the cached failure.
    """
    cached = _dl.conversion_statuses.get(paper_id)
    if cached is not None and getattr(cached, "status", None) == "error":
        _dl.conversion_statuses.pop(paper_id, None)


async def patched_handle_download(arguments: Dict[str, Any]) -> List[types.TextContent]:
    paper_id = arguments.get("paper_id", "") if isinstance(arguments, dict) else ""

    def _pre_attempt() -> None:
        if paper_id:
            _evict_stale_download_error(paper_id)

    return await _with_retry(
        f"download_paper({paper_id})",
        lambda: _orig_handle_download(arguments),
        pre_attempt_hook=_pre_attempt,
    )


# ── handle_search wrapper ────────────────────────────────────────────

_orig_handle_search = _sr.handle_search


async def patched_handle_search(arguments: Dict[str, Any]) -> List[types.TextContent]:
    query = (arguments or {}).get("query", "")
    return await _with_retry(
        f"search_papers({query[:40]!r})",
        lambda: _orig_handle_search(arguments),
    )


# ── handle_list_papers wrapper ───────────────────────────────────────

_orig_handle_list_papers = _lp.handle_list_papers


async def patched_handle_list_papers(arguments: Dict[str, Any] | None = None) -> List[types.TextContent]:
    return await _with_retry(
        "list_papers",
        lambda: _orig_handle_list_papers(arguments),
    )


# ── Install patches ──────────────────────────────────────────────────
# Rebind in BOTH the module of origin AND in arxiv_mcp_server.server,
# because server.py imports the handlers by name with
# ``from .tools import handle_search, ...`` — that creates references
# in server's own namespace which a tools-side reassignment alone
# wouldn't reach.

_dl.handle_download = patched_handle_download
_sr.handle_search = patched_handle_search
_lp.handle_list_papers = patched_handle_list_papers

_srv.handle_download = patched_handle_download
_srv.handle_search = patched_handle_search
_srv.handle_list_papers = patched_handle_list_papers
# handle_read_paper intentionally NOT patched — local-only, no flakiness.

# ── Invoke the upstream entrypoint ───────────────────────────────────

if __name__ == "__main__":
    from arxiv_mcp_server import main
    sys.exit(main())
