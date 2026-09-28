#!/usr/bin/env python3
"""Evaluator for ``fomc-decision-reaction``.

Same family as ``yahoo-analysis`` (recompute ground truth from the live source,
compare the agent's markdown table with tolerances), extended with a web leg:
the *decisions* come from the Federal Reserve website and the *market data*
from Yahoo Finance.

Ground truth is resolved live-first with a frozen fallback, so a Fed-site or
Yahoo outage during grading is distinguishable from a wrong report:

1. scrape the FOMC calendar for the scheduled 2025 meetings and read each
   policy statement to classify hold / cut / hike and the new target range;
2. pull ``^GSPC`` and ``^TNX`` daily closes from yfinance;
3. if either leg fails or fails a sanity check, fall back to
   ``groundtruth_workspace/gt_snapshot.json``.

Set ``TOOLATHLON_FOMC_FORCE_SNAPSHOT=1`` to grade against the snapshot only.

Tolerances: returns and yield changes +/-0.10 (percentage points or bp) so
that dividend-adjusted vs. raw closes or a half-day of rounding never fails a
correct report, while picking the wrong pre-decision day (a ~0.5-1 % swing on
these dates) still does. Decision type, target range, the set of decision
dates, the largest-move date and the meeting count are exact.
"""

from __future__ import annotations

import json
import os
import re
import sys
from argparse import ArgumentParser
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

YEAR = 2025
CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
STATEMENT_URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{ymd}a.htm"
SP500 = "^GSPC"
TNX = "^TNX"
FIVE_DAY_OFFSET = 5

PCT_TOL = 0.10          # S&P returns, percentage points
BP_TOL = 0.10           # yield change, basis points
AVG_TOL = 0.10          # per-type averages
CONSISTENCY_TOL = 0.5   # direction consistency, percentage points

FRACTIONS = {"1/4": 0.25, "1/2": 0.50, "3/4": 0.75, "1/8": 0.125, "3/8": 0.375, "5/8": 0.625, "7/8": 0.875}


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# Leg 1: Federal Reserve website
# --------------------------------------------------------------------------- #
def _http_get(url: str, attempts: int = 3) -> str:
    import time

    import httpx

    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        try:
            with httpx.Client(timeout=60, follow_redirects=True, proxy=proxy) as client:
                r = client.get(url, headers={"User-Agent": "Mozilla/5.0 (toolathlon-evaluator)"})
                r.raise_for_status()
                return r.text
        except Exception as exc:  # noqa: BLE001 - the Fed site intermittently drops TLS mid-handshake
            last_exc = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET {url} failed after {attempts} attempts: {last_exc}")


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("‑", "-").replace("–", "-").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


def _fraction_to_decimal(token: str) -> float:
    token = token.strip().replace("‑", "-")
    m = re.fullmatch(r"(\d+)(?:-(\d/\d))?", token)
    if not m:
        raise ValueError(f"cannot parse rate token {token!r}")
    whole = float(m.group(1))
    frac = FRACTIONS[m.group(2)] if m.group(2) else 0.0
    return whole + frac


def scrape_fed_decisions() -> List[Dict[str, Any]]:
    """Scheduled YEAR meetings -> [{date, decision, lower, upper}], chronological."""
    html = _http_get(CALENDAR_URL)
    start = html.find(f"{YEAR} FOMC Meetings")
    if start < 0:
        raise RuntimeError(f"calendar page has no '{YEAR} FOMC Meetings' section")
    later = [html.find(f"{y} FOMC Meetings") for y in range(YEAR - 1, YEAR - 4, -1)]
    later = [p for p in later if p > start]
    section = html[start: min(later) if later else len(html)]

    decisions = []
    # alternating rows carry an extra "fomc-meeting--shaded" class before "row"
    for block in re.split(r'<div class="[^"]*\brow fomc-meeting\b[^"]*"', section)[1:]:
        plain = _strip_html(block)
        # notation votes / unscheduled meetings are not scheduled decisions
        if "notation vote" in plain.lower() or "unscheduled" in plain.lower():
            continue
        m = re.search(rf"monetary({YEAR}\d{{4}})a\.htm", block)
        if not m:
            continue
        ymd = m.group(1)
        stmt = _strip_html(_http_get(STATEMENT_URL.format(ymd=ymd)))
        k = stmt.find("target range for the federal funds rate")
        if k < 0:
            raise RuntimeError(f"statement {ymd}: no target-range sentence")
        window = stmt[max(0, k - 200): k + 200]
        if re.search(r"\bmaintain\b", window):
            decision = "Hold"
        elif re.search(r"\blower\b", window):
            decision = "Cut"
        elif re.search(r"\braise\b", window):
            decision = "Hike"
        else:
            raise RuntimeError(f"statement {ymd}: cannot classify decision: {window!r}")
        rng = re.search(r"(?:at|to)\s+(\d+(?:-\d/\d)?)\s+to\s+(\d+(?:-\d/\d)?)\s+percent", window)
        if not rng:
            raise RuntimeError(f"statement {ymd}: cannot parse target range: {window!r}")
        decisions.append({
            "date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}",
            "decision": decision,
            "lower": _fraction_to_decimal(rng.group(1)),
            "upper": _fraction_to_decimal(rng.group(2)),
        })
    if not decisions:
        raise RuntimeError("no scheduled meetings with statements found")
    decisions.sort(key=lambda d: d["date"])
    return decisions


# --------------------------------------------------------------------------- #
# Leg 2: Yahoo Finance
# --------------------------------------------------------------------------- #
def fetch_closes(ticker: str, start: str, end: str) -> Dict[str, float]:
    import yfinance as yf

    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    close = hist["Close"].dropna()
    if len(close) < 200:
        raise RuntimeError(f"{ticker}: only {len(close)} daily bars, expected a full year")
    idx = close.index.tz_localize(None) if close.index.tz is not None else close.index
    return {d.strftime("%Y-%m-%d"): float(v) for d, v in zip(idx, close.values)}


# --------------------------------------------------------------------------- #
# Ground truth assembly
# --------------------------------------------------------------------------- #
def load_snapshot(groundtruth_workspace: Optional[str]) -> Dict[str, Any]:
    path = Path(groundtruth_workspace or Path(__file__).resolve().parent.parent / "groundtruth_workspace") / "gt_snapshot.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_ground_truth(groundtruth_workspace: Optional[str]) -> Dict[str, Any]:
    snapshot = load_snapshot(groundtruth_workspace)
    if os.environ.get("TOOLATHLON_FOMC_FORCE_SNAPSHOT") == "1":
        log(f"ground truth source: frozen snapshot (forced), snapshot date {snapshot.get('snapshot_date')}")
        return snapshot

    try:
        decisions = scrape_fed_decisions()
        sp = fetch_closes(SP500, f"{YEAR}-01-01", f"{YEAR + 1}-02-01")
        tnx = fetch_closes(TNX, f"{YEAR}-01-01", f"{YEAR + 1}-02-01")
    except Exception as exc:  # noqa: BLE001
        log(f"ground truth source: frozen snapshot, snapshot date {snapshot.get('snapshot_date')}")
        log(f"  reason: live pull failed ({type(exc).__name__}: {exc}). If the agent hit the same outage, "
            f"its report may be empty or wrong for reasons unrelated to its reasoning.")
        return snapshot

    snap_dates = [d["date"] for d in snapshot["decisions"]]
    live_dates = [d["date"] for d in decisions]
    if live_dates != snap_dates:
        log(f"ground truth source: frozen snapshot, snapshot date {snapshot.get('snapshot_date')}")
        log(f"  reason: live Fed calendar returned {live_dates}, snapshot has {snap_dates}; "
            f"regenerate the snapshot with build_snapshot.py if the calendar changed.")
        return snapshot

    log("ground truth source: LIVE Federal Reserve calendar + yfinance, the same sources the agent reads")
    return {"snapshot_date": "live", "decisions": decisions, "sp500_close": sp, "tnx_close": tnx}


def _prev_trading_close(closes: Dict[str, float], day: str) -> Tuple[str, float]:
    days = sorted(closes)
    prior = [d for d in days if d < day]
    if not prior:
        raise RuntimeError(f"no close before {day}")
    return prior[-1], closes[prior[-1]]


def _on_or_after_close(closes: Dict[str, float], day: str) -> Tuple[int, str, float]:
    days = sorted(closes)
    for i, d in enumerate(days):
        if d >= day:
            return i, d, closes[d]
    raise RuntimeError(f"no close on or after {day}")


def derive_expected(gt: Dict[str, Any]) -> Dict[str, Any]:
    sp, tnx = gt["sp500_close"], gt["tnx_close"]
    sp_days = sorted(sp)
    rows = []
    for d in gt["decisions"]:
        day = d["date"]
        _, sp_pre = _prev_trading_close(sp, day)
        i_on, _, sp_on = _on_or_after_close(sp, day)
        sp_5 = sp[sp_days[i_on + FIVE_DAY_OFFSET]]
        _, y_pre = _prev_trading_close(tnx, day)
        _, _, y_on = _on_or_after_close(tnx, day)
        rows.append({
            "date": day,
            "decision": d["decision"],
            "range": f"{d['lower']:.2f}-{d['upper']:.2f}",
            "ret1": (sp_on / sp_pre - 1) * 100,
            "ret5": (sp_5 / sp_on - 1) * 100,
            "bp": (y_on - y_pre) * 100,
        })

    by_type: Dict[str, List[float]] = {}
    for r in rows:
        by_type.setdefault(r["decision"], []).append(r["ret1"])
    averages = {k: sum(v) / len(v) for k, v in by_type.items()}
    largest = max(rows, key=lambda r: abs(r["ret1"]))["date"]
    opposite = sum(1 for r in rows if r["ret1"] * r["bp"] < 0)
    consistency = opposite / len(rows) * 100
    return {
        "rows": rows,
        "averages": averages,
        "largest": largest,
        "consistency": consistency,
        "count": len(rows),
        "first": rows[0]["date"],
        "last": rows[-1]["date"],
    }


# --------------------------------------------------------------------------- #
# Report parsing (same conventions as yahoo-analysis)
# --------------------------------------------------------------------------- #
def load_results_md(workspace: Path) -> str:
    p = workspace / "results.md"
    if not p.exists():
        log("Target file does not exist. Test fail.")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def parse_table(md: str):
    import pandas as pd

    m = re.search(r"## Table\s*(\|[\s\S]+?)\n## ", md)
    if not m:
        log("No table found in the Markdown content.")
        sys.exit(1)
    df = pd.read_csv(StringIO(m.group(1).strip()), sep="|", engine="python", header=0,
                     skipinitialspace=True, usecols=lambda x: x.strip() != "")
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    df = df[df["Decision Date"].str.match(r"\d{4}-\d{2}-\d{2}")]
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df


def parse_field(md: str, label: str) -> str:
    m = re.search(rf"^{re.escape(label)}:\s*(.+?)\s*$", md, flags=re.MULTILINE)
    if not m:
        log(f"No '{label}' found in the Markdown content.")
        sys.exit(1)
    return m.group(1).strip()


def to_float(raw: str) -> Optional[float]:
    raw = raw.replace("%", "").replace("bp", "").replace("+", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def normalize_range(raw: str) -> Optional[str]:
    nums = re.findall(r"\d+(?:\.\d+)?", raw)
    if len(nums) != 2:
        return None
    return f"{float(nums[0]):.2f}-{float(nums[1]):.2f}"


def fail(msg: str) -> None:
    log(f"❌ {msg}")
    sys.exit(1)


# --------------------------------------------------------------------------- #
def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    log(f"Using agent workspace: {args.agent_workspace}")
    ws = Path(args.agent_workspace)

    log("🔍 Loading results from workspace...")
    md = load_results_md(ws)

    log("🔍 Parsing table, summary, and data range...")
    df = parse_table(md)

    log("⏳ Resolving ground truth (Federal Reserve calendar + Yahoo Finance)...")
    gt = resolve_ground_truth(args.groundtruth_workspace)
    exp = derive_expected(gt)

    log("🔍 Verifying reported table against ground truth...")
    reported_dates = list(df["Decision Date"])
    expected_dates = [r["date"] for r in exp["rows"]]
    log(f"  Decision dates: reported {reported_dates}")
    log(f"                  expected {expected_dates}")
    if reported_dates != expected_dates:
        fail("Decision dates do not match the scheduled 2025 meetings (check for missing meetings, "
             "notation votes counted as meetings, or wrong meeting-end dates).")

    for (_, row), er in zip(df.iterrows(), exp["rows"]):
        d = er["date"]
        log(f"\n— {d} —")
        dec = row["Decision"].strip().capitalize()
        log(f"  Decision: reported {dec}, actual {er['decision']}")
        if dec != er["decision"]:
            fail("Decision type mismatch")

        rng = normalize_range(row["Target Range (%)"])
        log(f"  Target Range: reported {rng}, actual {er['range']}")
        if rng != er["range"]:
            fail("Target range mismatch")

        for col, key, tol, unit in (("S&P 1-Day Return (%)", "ret1", PCT_TOL, "%"),
                                    ("S&P 5-Day Return (%)", "ret5", PCT_TOL, "%"),
                                    ("10Y Yield Change (bp)", "bp", BP_TOL, "bp")):
            val = to_float(row[col])
            log(f"  {col}: reported {val}{unit}, actual {er[key]:.2f}{unit}")
            if val is None or abs(val - er[key]) > tol:
                fail(f"{col} diff > {tol}{unit}")

    log("\n🔍 Verifying Summary...")
    for typ in ("Hold", "Cut", "Hike"):
        raw = parse_field(md, f"{typ} Avg 1-Day Return (%)")
        if typ in exp["averages"]:
            val = to_float(raw)
            log(f"  {typ} avg: reported {val}, actual {exp['averages'][typ]:.2f}")
            if val is None or abs(val - exp["averages"][typ]) > AVG_TOL:
                fail(f"{typ} Avg 1-Day Return diff > {AVG_TOL}")
        else:
            log(f"  {typ} avg: reported {raw!r}, expected N/A")
            if raw.upper() not in ("N/A", "NA", "NONE", "-"):
                fail(f"{typ} did not occur in {YEAR}; expected N/A")

    largest = parse_field(md, "Largest 1-Day Move")
    log(f"  Largest 1-Day Move: reported {largest}, actual {exp['largest']}")
    if largest[:10] != exp["largest"]:
        fail("Largest 1-Day Move mismatch")

    cons = to_float(parse_field(md, "Direction Consistency (%)"))
    log(f"  Direction Consistency: reported {cons}%, actual {exp['consistency']:.2f}%")
    if cons is None or abs(cons - exp["consistency"]) > CONSISTENCY_TOL:
        fail(f"Direction Consistency diff > {CONSISTENCY_TOL}%")

    log("\n🔍 Verifying Data Range...")
    count = parse_field(md, "Meetings")
    log(f"  Meetings: reported {count}, actual {exp['count']}")
    if not count.isdigit() or int(count) != exp["count"]:
        fail("Meeting count mismatch")
    first, last = parse_field(md, "First Decision")[:10], parse_field(md, "Last Decision")[:10]
    log(f"  First/Last: reported {first} / {last}, actual {exp['first']} / {exp['last']}")
    if first != exp["first"] or last != exp["last"]:
        fail("First/Last decision date mismatch")

    log("\n✅ All checks passed.")


if __name__ == "__main__":
    main()
