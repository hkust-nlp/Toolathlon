"""Toolathlon-side launch wrapper for pdf-tools-mcp.

Upstream ``pdf_tools_mcp`` (https://github.com/lockon-n/pdf-tools-mcp) uses
a non-reentrant ``threading.Lock()`` for its in-memory caches:

    cache_lock = threading.Lock()   # server.py line ~48

But ``cache_pdf_content()`` and ``search_pdf_content()`` both acquire
``cache_lock`` and then — while still holding it — call
``cleanup_cache()`` when the cache exceeds its size threshold.
``cleanup_cache()`` *also* does ``with cache_lock:`` at its top.  Because
the lock is non-reentrant, the second acquire blocks forever, deadlocking
the entire MCP server.

Trigger conditions:
  * ``pdf_content_cache`` reaches ``MAX_CACHED_PDFS`` (10) entries, or
  * ``search_sessions`` exceeds 20 entries (one per ``search_pdf_content``
    call — even calls with patterns that match get a fresh UUID-keyed
    session every time).

In long-running agent loops over a multi-PDF task (e.g. detect-revised-terms,
academic-pdf-report), 20 search calls is easy to hit.  After the
deadlock, every subsequent tool call hangs until the agent's MCP client
times out, then returns "Tool call failed: search_pdf_content" with the
underlying cause lost in two layers of error wrapping.

This wrapper monkey-patches ``cache_lock`` to ``threading.RLock()`` (the
reentrant variant) before ``mcp.run()`` is invoked.  RLock lets the same
thread re-acquire the lock — turning the previously-deadlocking path into
a normal recursive acquire that just increments the counter.

We do NOT touch any other behaviour: same handlers, same cache eviction
policy, same wire protocol.  The patch is a single attribute reassignment.

The upstream PyPI package is unchanged; we just intercept its launch.
"""
from __future__ import annotations

import threading

import pdf_tools_mcp.server as _srv

# Replace the non-reentrant Lock with an RLock.  Both objects support the
# same `with` protocol so existing call sites work unchanged.
_srv.cache_lock = threading.RLock()


if __name__ == "__main__":
    _srv.main()
