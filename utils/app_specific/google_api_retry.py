"""Layer-1 retry helpers for Google API client calls (gspread + google-api-python-client).

Unlike the other shared-helper modules (WC, Canvas, Notion, Poste), the
Google API surface in this repo is consumed *directly* from each grader
via ``gspread`` / ``googleapiclient`` rather than through a single client
class.  There's no one place to decorate, so this module exposes two
shapes that callers can drop in with one line:

  1. ``@google_retry`` — decorator to wrap a function that makes one or
     more Google-API calls and whose retry semantics should cover the
     whole body.  Most useful for evaluator helpers like
     ``def fetch_sheet_rows(...)`` in a task grader.

  2. ``safe_execute(request)`` — wraps a single
     ``service.spreadsheets()...execute()`` call so existing call sites can
     be patched mechanically:

         # before
         result = service.spreadsheets().values().get(...).execute()
         # after
         result = safe_execute(service.spreadsheets().values().get(...))

Both retry the same set of transient conditions:

  * Network: ``ConnectionError``, ``Timeout``, ``socket.error``
  * Google HTTP 5xx and 429 (rate limit) — extracted from
    ``googleapiclient.errors.HttpError.resp.status``.
  * gspread's ``APIError`` when the wrapped status is 5xx / 429.

We do NOT retry on:
  * 4xx-other-than-429 (404, 401, 403, 400) — those are deterministic
    permission / spec errors that retrying only hides.
  * Any exception that isn't transport- or rate-limit-related (e.g.
    ``KeyError`` from a malformed response body).
"""

import socket
from typing import Any, Callable

from requests.exceptions import ConnectionError, Timeout
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    retry_if_exception_type,
)

try:
    from googleapiclient.errors import HttpError as _GoogleHttpError
except Exception:  # googleapiclient may not be installed in every env
    _GoogleHttpError = None  # type: ignore

try:
    from gspread.exceptions import APIError as _GspreadAPIError
except Exception:
    _GspreadAPIError = None  # type: ignore


def _is_transient_google_error(exc: BaseException) -> bool:
    """Decide whether ``exc`` is worth a retry.

    Tolerant of partial installs: if a library isn't imported (its symbol
    above is ``None``), exception checks against it short-circuit and we
    fall through to the generic transport-error checks.
    """
    # Transport-level: always retry.  These cover both raw ``requests`` and
    # google's transport adapter when the network is unreachable.
    if isinstance(exc, (ConnectionError, Timeout, socket.error, OSError)):
        return True

    # google-api-python-client uses HttpError with .resp.status.
    if _GoogleHttpError is not None and isinstance(exc, _GoogleHttpError):
        try:
            status = exc.resp.status
        except AttributeError:
            return False
        return status >= 500 or status == 429

    # gspread wraps Sheets API errors; the wrapped status sits in .response.
    if _GspreadAPIError is not None and isinstance(exc, _GspreadAPIError):
        try:
            status = exc.response.status_code
        except AttributeError:
            return False
        return status >= 500 or status == 429

    return False


# Bounded to 3 attempts × ~10s per call + 1+2s backoff so a fully-down
# Google endpoint fails out in ~33s wall-clock, well inside the Layer-2
# sleep budget callers wrap around the whole check.
google_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception(_is_transient_google_error),
    reraise=True,
)


@google_retry
def safe_execute(request: Any) -> Any:
    """Run ``request.execute()`` under the Google Layer-1 retry policy.

    ``request`` is whatever ``service.spreadsheets()...`` (or any
    googleapiclient resource chain) returned that has an ``.execute()``
    method.  We don't widen this to accept a callable because that would
    hide the most common bug — forgetting to chain the request — behind a
    deceptive retry loop.
    """
    return request.execute()
