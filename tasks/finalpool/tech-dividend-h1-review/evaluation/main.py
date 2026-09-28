#!/usr/bin/env python3
"""Evaluator for ``tech-dividend-h1-review``.

Task family: real-data snapshot, *fixed date window + frozen snapshot with
tolerances* (the same approach as the Sheet-1 check of ``nvidia-stock-analysis``).

The agent reviews the 2025 H1 dividend income of a six-stock portfolio from
Yahoo Finance data and writes ``dividend_review.json``.  Every input fact is
historical and therefore stable:

* ex-dividend dates and cash amounts per share with ex-dates in
  2025-01-01 .. 2025-06-30 (inclusive), and
* the 2025-06-30 closing price of each stock.

Ground truth is resolved live-first, so the grader and the agent read the same
source (the same two-legged arrangement as ``nvidia-stock-analysis``):

1. pull the ex-dates, amounts and 2025-06-30 closes from yfinance, and
2. fall back to the frozen ``groundtruth_workspace/gt_snapshot.json`` when
   yfinance is unreachable or returns data that fails a sanity check.

Which leg was used is always printed, so a failure caused by an unreachable
Yahoo Finance is distinguishable from a genuinely wrong report.  Everything
else (per-share totals, cash received, yields, income shares, portfolio total,
best-yield / largest-contributor tickers) is derived here from whichever leg
won, so the grader still has a single source of truth.  Drift between the two
legs is printed when both are available.

Tolerances absorb legitimate representation differences rather than wrong
answers: ex-dates +/-1 day (timezones), dividend amounts 0.5 % (2- vs
4-decimal rounding), closing prices 5 % (Yahoo's default dividend-adjusted
Close vs. the regular Close), yields 6 % relative (they inherit the close
difference), income shares +/-0.15 percentage points.

Set ``TOOLATHLON_DIVIDEND_FORCE_SNAPSHOT=1`` to skip the live fetch and grade
against the frozen snapshot only (deterministic offline runs).  Regenerate or
diff the snapshot with ``build_snapshot.py``.  Exit code 0 = pass, 1 = fail
(reasons are printed).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

TICKER_ORDER = ["MSFT", "AAPL", "CSCO", "PEP", "COST", "TXN"]
PERIOD_START = date(2025, 1, 1)
PERIOD_END = date(2025, 6, 30)
DATE_TOLERANCE_DAYS = 1

# key -> (absolute floor, relative tolerance against the expected value)
TOLERANCES: Dict[str, Tuple[float, float]] = {
    "amount_per_share": (0.0006, 0.005),
    "dividend_per_share_total": (0.006, 0.005),
    "cash_received": (0.06, 0.005),
    "close_2025_06_30": (0.0, 0.05),
    "h1_yield_pct": (0.02, 0.06),
    "income_share_pct": (0.15, 0.0),
    "total_cash_received": (0.10, 0.005),
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(msg, flush=True)


def to_number(raw: Any) -> Optional[float]:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if value == value and abs(value) != float("inf") else None
    if isinstance(raw, str):
        cleaned = re.sub(r"[,\s]", "", raw)
        cleaned = re.sub(r"(?i)(usd|us\$|hk\$|\$|%|pct|percent)", "", cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def to_int(raw: Any) -> Optional[int]:
    value = to_number(raw)
    if value is None or not float(value).is_integer():
        return None
    return int(value)


def parse_date(raw: Any) -> Optional[date]:
    if raw is None or isinstance(raw, (int, float, bool)):
        return None
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def within(actual: Optional[float], expected: float, key: str) -> Tuple[bool, str]:
    if actual is None:
        return False, f"{key}: missing or not numeric"
    abs_floor, rel = TOLERANCES[key]
    allowed = max(abs_floor, rel * abs(expected))
    diff = abs(actual - expected)
    ok = diff <= allowed + 1e-9
    verdict = "ok" if ok else "MISMATCH"
    return ok, f"{key}: got {actual:.4f}, expected {expected:.4f}, diff {diff:.4f} <= {allowed:.4f}? {verdict}"


def strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw


# --------------------------------------------------------------------------- #
# ground truth
# --------------------------------------------------------------------------- #
def load_snapshot(groundtruth_workspace: str) -> Dict[str, Any]:
    path = os.path.join(groundtruth_workspace, "gt_snapshot.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def fetch_live_holdings() -> Dict[str, Dict[str, Any]]:
    """Pull the same facts the agent reads. Raises if yfinance is unavailable."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_snapshot import fetch_from_yfinance  # type: ignore

    return fetch_from_yfinance(TICKER_ORDER)


def sanity_check_live(live: Dict[str, Dict[str, Any]], snapshot: Dict[str, Any]) -> List[str]:
    """Reject a live pull that is obviously broken rather than merely revised.

    Dividend history for a closed half-year does not change, so a differing
    payment count means a truncated or rate-limited response, not news.  Prices
    are only range-checked, since Yahoo may serve adjusted closes.
    """
    problems: List[str] = []
    for ticker in TICKER_ORDER:
        cur = live.get(ticker)
        if not cur:
            problems.append(f"{ticker}: absent from the live response")
            continue
        expected_count = len(snapshot["holdings"][ticker]["dividends"])
        if len(cur.get("dividends") or []) != expected_count:
            problems.append(
                f"{ticker}: live pull has {len(cur.get('dividends') or [])} dividends in the window, "
                f"snapshot has {expected_count} (likely a truncated response)"
            )
        close = to_number(cur.get("close_2025_06_30"))
        if close is None or close <= 0:
            problems.append(f"{ticker}: live close is {cur.get('close_2025_06_30')!r}")
        if cur.get("close_date_used") and parse_date(cur["close_date_used"]) != PERIOD_END:
            problems.append(f"{ticker}: live close came from {cur['close_date_used']}, not {PERIOD_END}")
    return problems


def resolve_ground_truth(groundtruth_workspace: str) -> Dict[str, Any]:
    """Live-first with snapshot fallback; prints which leg supplied the truth."""
    snapshot = load_snapshot(groundtruth_workspace)

    if os.environ.get("TOOLATHLON_DIVIDEND_FORCE_SNAPSHOT") == "1":
        log(
            "ground truth source: FROZEN SNAPSHOT (forced via TOOLATHLON_DIVIDEND_FORCE_SNAPSHOT), "
            f"captured {snapshot.get('snapshot_date')}"
        )
        return snapshot

    try:
        live = fetch_live_holdings()
    except Exception as exc:  # noqa: BLE001
        log(f"ground truth source: FROZEN SNAPSHOT captured {snapshot.get('snapshot_date')}")
        log(
            f"  reason: the live yfinance pull failed ({type(exc).__name__}: {exc}). If the agent hit the same "
            "outage or rate limit, a failure below reflects unavailable data rather than a wrong report."
        )
        return snapshot

    problems = sanity_check_live(live, snapshot)
    if problems:
        log(f"ground truth source: FROZEN SNAPSHOT captured {snapshot.get('snapshot_date')}")
        log("  reason: the live yfinance pull did not pass its sanity check:")
        for problem in problems:
            log(f"    - {problem}")
        return snapshot

    resolved = json.loads(json.dumps(snapshot))
    for ticker in TICKER_ORDER:
        resolved["holdings"][ticker]["dividends"] = live[ticker]["dividends"]
        resolved["holdings"][ticker]["close_2025_06_30"] = live[ticker]["close_2025_06_30"]
    resolved["snapshot_date"] = f"live yfinance pull (snapshot on file: {snapshot.get('snapshot_date')})"
    log("ground truth source: LIVE yfinance pull, the same source the agent reads")
    report_drift(snapshot, live)
    return resolved


def report_drift(snapshot: Dict[str, Any], live: Dict[str, Dict[str, Any]]) -> None:
    """Print where the live pull and the frozen snapshot disagree."""
    for ticker in TICKER_ORDER:
        snap = snapshot["holdings"][ticker]
        cur = live[ticker]
        snap_divs = [[d, round(float(a), 4)] for d, a in snap["dividends"]]
        live_divs = [[d, round(float(a), 4)] for d, a in cur["dividends"]]
        if snap_divs != live_divs:
            log(f"  drift {ticker} dividends: snapshot {snap_divs} | live {live_divs}")
        snap_close = float(snap["close_2025_06_30"])
        live_close = float(cur["close_2025_06_30"])
        if abs(snap_close - live_close) > 0.011:
            log(f"  drift {ticker} close: snapshot {snap_close} | live {live_close}")


def derive_expected(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    holdings: Dict[str, Dict[str, Any]] = {}
    total_cash = 0.0
    for ticker in TICKER_ORDER:
        raw = snapshot["holdings"][ticker]
        dividends = [(parse_date(d), float(a)) for d, a in raw["dividends"]]
        dps_total = sum(a for _, a in dividends)
        cash = dps_total * raw["shares"]
        close = float(raw["close_2025_06_30"])
        holdings[ticker] = {
            "shares": int(raw["shares"]),
            "dividends": dividends,
            "payments_count": len(dividends),
            "dividend_per_share_total": dps_total,
            "cash_received": cash,
            "close_2025_06_30": close,
            "h1_yield_pct": dps_total / close * 100.0,
        }
        total_cash += cash
    for ticker, data in holdings.items():
        data["income_share_pct"] = data["cash_received"] / total_cash * 100.0
    return {
        "holdings": holdings,
        "total_cash_received": total_cash,
        "highest_h1_yield_ticker": max(holdings, key=lambda t: holdings[t]["h1_yield_pct"]),
        "largest_cash_contributor_ticker": max(holdings, key=lambda t: holdings[t]["cash_received"]),
    }


# --------------------------------------------------------------------------- #
# agent output
# --------------------------------------------------------------------------- #
def load_report(workspace: str) -> Tuple[Optional[Dict[str, Any]], str]:
    path = os.path.join(workspace, "dividend_review.json")
    if not os.path.isfile(path):
        return None, "dividend_review.json not found in the workspace"
    with open(path, encoding="utf-8-sig") as handle:
        raw = strip_fences(handle.read())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"dividend_review.json is not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "dividend_review.json must be a JSON object"
    return data, ""


def normalize_holdings(raw: Any) -> Tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
    """Return ({TICKER: holding}, order_seen, errors)."""
    errors: List[str] = []
    result: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    if isinstance(raw, dict):
        items = [(k, v) for k, v in raw.items()]
        entries = []
        for key, value in items:
            if isinstance(value, dict):
                value = dict(value)
                value.setdefault("ticker", key)
                entries.append(value)
            else:
                errors.append(f"holding {key!r} is not an object")
    elif isinstance(raw, list):
        entries = raw
    else:
        return result, order, ["'holdings' must be a list of objects"]
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"holding #{index + 1} is not an object")
            continue
        ticker = str(entry.get("ticker") or entry.get("symbol") or "").strip().upper()
        if not ticker:
            errors.append(f"holding #{index + 1} has no ticker")
            continue
        if ticker in result:
            errors.append(f"duplicate holding for {ticker}")
            continue
        result[ticker] = entry
        order.append(ticker)
    return result, order, errors


def normalize_dividends(raw: Any) -> Tuple[List[Tuple[Optional[date], Optional[float]]], List[str]]:
    errors: List[str] = []
    items: List[Tuple[Optional[date], Optional[float]]] = []
    if raw is None:
        return items, ["'dividends' is missing"]
    if isinstance(raw, dict):
        raw = [{"ex_date": k, "amount_per_share": v} for k, v in raw.items()]
    if not isinstance(raw, list):
        return items, ["'dividends' must be a list"]
    for index, item in enumerate(raw):
        if isinstance(item, dict):
            date_raw = None
            for key in ("ex_date", "ex_dividend_date", "exDate", "date", "ex-date"):
                if key in item:
                    date_raw = item[key]
                    break
            amount_raw = None
            for key in ("amount_per_share", "amount", "dividend", "dividend_per_share", "cash_per_share", "value"):
                if key in item:
                    amount_raw = item[key]
                    break
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            date_raw, amount_raw = item
        else:
            errors.append(f"dividend #{index + 1} has an unrecognised shape: {item!r}")
            continue
        parsed_date = parse_date(date_raw)
        amount = to_number(amount_raw)
        if parsed_date is None:
            errors.append(f"dividend #{index + 1}: unparseable ex_date {date_raw!r}")
        if amount is None:
            errors.append(f"dividend #{index + 1}: unparseable amount {amount_raw!r}")
        items.append((parsed_date, amount))
    return items, errors


def match_dividends(
    agent: Sequence[Tuple[Optional[date], Optional[float]]],
    expected: Sequence[Tuple[date, float]],
) -> List[str]:
    """One-to-one matching on (date +/-1 day, amount within tolerance)."""
    errors: List[str] = []
    remaining = list(range(len(agent)))
    for exp_date, exp_amount in expected:
        found = None
        for idx in remaining:
            a_date, a_amount = agent[idx]
            if a_date is None or a_amount is None:
                continue
            if abs((a_date - exp_date).days) <= DATE_TOLERANCE_DAYS and within(a_amount, exp_amount, "amount_per_share")[0]:
                found = idx
                break
        if found is None:
            errors.append(f"expected dividend ex {exp_date} {exp_amount:.4f}/share not found")
        else:
            remaining.remove(found)
    for idx in remaining:
        a_date, a_amount = agent[idx]
        errors.append(f"unexpected dividend entry ex {a_date} {a_amount} (outside the window or not a real payment)")
    return errors


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the tech-dividend-h1-review task")
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--groundtruth_workspace", required=True)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    ground_truth = resolve_ground_truth(args.groundtruth_workspace)
    expected = derive_expected(ground_truth)
    log(f"window {PERIOD_START} .. {PERIOD_END}")
    log(
        f"expected total {expected['total_cash_received']:.2f}, best yield {expected['highest_h1_yield_ticker']}, "
        f"largest contributor {expected['largest_cash_contributor_ticker']}"
    )

    report, err = load_report(args.agent_workspace)
    if report is None:
        log(f"FAIL: {err}")
        return 1

    failures: List[str] = []

    # period
    period = report.get("period") or {}
    if not isinstance(period, dict):
        failures.append("'period' must be an object with start/end")
    else:
        if parse_date(period.get("start")) != PERIOD_START:
            failures.append(f"period.start {period.get('start')!r} != {PERIOD_START}")
        if parse_date(period.get("end")) != PERIOD_END:
            failures.append(f"period.end {period.get('end')!r} != {PERIOD_END}")

    # holdings
    holdings, order, errors = normalize_holdings(report.get("holdings"))
    failures.extend(errors)
    missing = [t for t in TICKER_ORDER if t not in holdings]
    extra = [t for t in holdings if t not in TICKER_ORDER]
    if missing:
        failures.append(f"missing holdings: {missing}")
    if extra:
        failures.append(f"unexpected holdings: {extra}")
    if order and order != [t for t in TICKER_ORDER if t in holdings]:
        log(f"note: holdings order {order} differs from the requested order {TICKER_ORDER} (not penalised)")

    for ticker in TICKER_ORDER:
        entry = holdings.get(ticker)
        if entry is None:
            continue
        exp = expected["holdings"][ticker]
        log(f"\n=== {ticker} ===")
        local: List[str] = []

        shares = to_int(entry.get("shares"))
        if shares != exp["shares"]:
            local.append(f"shares: got {entry.get('shares')!r}, expected {exp['shares']}")

        dividends, div_errors = normalize_dividends(entry.get("dividends"))
        local.extend(div_errors)
        local.extend(match_dividends(dividends, exp["dividends"]))

        count = to_int(entry.get("payments_count"))
        if count != exp["payments_count"]:
            local.append(f"payments_count: got {entry.get('payments_count')!r}, expected {exp['payments_count']}")

        for key in ("dividend_per_share_total", "cash_received", "close_2025_06_30", "h1_yield_pct", "income_share_pct"):
            ok, message = within(to_number(entry.get(key)), exp[key], key)
            log(f"  {message}")
            if not ok:
                local.append(message)

        if local:
            for message in local:
                log(f"  ERROR: {message}")
            failures.extend(f"{ticker}: {m}" for m in local)
        else:
            log("  OK")

    log("\n=== portfolio ===")
    ok, message = within(to_number(report.get("total_cash_received")), expected["total_cash_received"], "total_cash_received")
    log(f"  {message}")
    if not ok:
        failures.append(message)

    for key in ("highest_h1_yield_ticker", "largest_cash_contributor_ticker"):
        got = str(report.get(key) or "").strip().upper()
        if got != expected[key]:
            failures.append(f"{key}: got {report.get(key)!r}, expected {expected[key]}")
        else:
            log(f"  {key}: {got} ok")

    log("")
    if failures:
        log("EVALUATION FAILED:")
        for failure in failures:
            log(f"  - {failure}")
        return 1
    log("All checks passed: dividend_review.json matches the 2025 H1 snapshot within tolerance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
