#!/usr/bin/env python3
"""Verify or regenerate ``groundtruth_workspace/gt_snapshot.json`` from Yahoo Finance.

The checked-in snapshot was cross-built from the Nasdaq dividend-history API and
two independent daily-quote sources (see the ``provenance`` block inside the
file).  Because the agent works from Yahoo Finance, run this script once on a
host that can reach Yahoo Finance to confirm that yfinance reports the same
ex-dates, amounts and 2025-06-30 closes::

    # compare only (exit code 1 if anything differs)
    uv run python tasks/finalpool/tech-dividend-h1-review/evaluation/build_snapshot.py --check

    # rewrite dividends/closes in the snapshot from yfinance and stamp today's date
    uv run python tasks/finalpool/tech-dividend-h1-review/evaluation/build_snapshot.py

Shares held, the period and the boundary notes are never changed by this
script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PATH = os.path.join(os.path.dirname(HERE), "groundtruth_workspace", "gt_snapshot.json")

TICKERS = ["MSFT", "AAPL", "CSCO", "PEP", "COST", "TXN"]
PERIOD_START = date(2025, 1, 1)
PERIOD_END = date(2025, 6, 30)
CLOSE_DATE = date(2025, 6, 30)


def fetch_from_yfinance(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """{ticker: {dividends: [[YYYY-MM-DD, amount], ...], close_2025_06_30, adjusted_close_2025_06_30, close_date_used}}"""
    import pandas as pd
    import yfinance as yf

    out: Dict[str, Dict[str, Any]] = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        # Raw (unadjusted) history including the Dividends / Stock Splits columns.
        hist = stock.history(start="2024-12-01", end="2025-07-15", interval="1d", auto_adjust=False, actions=True)
        if hist is None or hist.empty:
            raise RuntimeError(f"yfinance returned no history for {ticker}")
        if getattr(hist.index, "tz", None) is not None:
            hist.index = hist.index.tz_localize(None)

        dividends: List[List[Any]] = []
        if "Dividends" in hist.columns:
            for ts, amount in hist["Dividends"].items():
                if amount is None or pd.isna(amount) or float(amount) <= 0:
                    continue
                ex_date = ts.to_pydatetime().date()
                if PERIOD_START <= ex_date <= PERIOD_END:
                    dividends.append([ex_date.isoformat(), round(float(amount), 4)])
        dividends.sort()

        mask = [ts.to_pydatetime().date() <= CLOSE_DATE for ts in hist.index]
        closes = hist.loc[mask, "Close"].dropna()
        if closes.empty:
            raise RuntimeError(f"no close on/before {CLOSE_DATE} for {ticker}")
        close_raw = float(closes.iloc[-1])
        close_date_used = closes.index[-1].to_pydatetime().date().isoformat()

        adjusted = stock.history(start="2025-06-24", end="2025-07-02", interval="1d", auto_adjust=True)
        adjusted_close = None
        if adjusted is not None and not adjusted.empty:
            if getattr(adjusted.index, "tz", None) is not None:
                adjusted.index = adjusted.index.tz_localize(None)
            adj_mask = [ts.to_pydatetime().date() <= CLOSE_DATE for ts in adjusted.index]
            adj_closes = adjusted.loc[adj_mask, "Close"].dropna()
            if not adj_closes.empty:
                adjusted_close = round(float(adj_closes.iloc[-1]), 2)

        out[ticker] = {
            "dividends": dividends,
            "close_2025_06_30": round(close_raw, 2),
            "adjusted_close_2025_06_30": adjusted_close,
            "close_date_used": close_date_used,
        }
        print(f"{ticker}: dividends {dividends}, raw close {close_raw:.2f} ({close_date_used}), adjusted {adjusted_close}")
    return out


def compare(snapshot: Dict[str, Any], live: Dict[str, Dict[str, Any]]) -> List[str]:
    diffs: List[str] = []
    for ticker in TICKERS:
        snap = snapshot["holdings"][ticker]
        cur = live[ticker]
        snap_divs = [[d, round(float(a), 4)] for d, a in snap["dividends"]]
        if snap_divs != cur["dividends"]:
            diffs.append(f"{ticker} dividends: snapshot {snap_divs} vs yfinance {cur['dividends']}")
        if abs(float(snap["close_2025_06_30"]) - float(cur["close_2025_06_30"])) > 0.011:
            diffs.append(
                f"{ticker} close: snapshot {snap['close_2025_06_30']} vs yfinance raw {cur['close_2025_06_30']}"
            )
        if cur["close_date_used"] != CLOSE_DATE.isoformat():
            diffs.append(f"{ticker}: yfinance had no bar on {CLOSE_DATE}, used {cur['close_date_used']}")
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="only compare yfinance with the checked-in snapshot")
    args = parser.parse_args()

    with open(SNAPSHOT_PATH, encoding="utf-8") as handle:
        snapshot = json.load(handle)

    live = fetch_from_yfinance(TICKERS)
    diffs = compare(snapshot, live)
    if diffs:
        print("\nDifferences versus the checked-in snapshot:")
        for diff in diffs:
            print(f"  - {diff}")
    else:
        print("\nyfinance agrees with the checked-in snapshot.")

    if args.check:
        return 1 if diffs else 0

    for ticker in TICKERS:
        snapshot["holdings"][ticker]["dividends"] = live[ticker]["dividends"]
        snapshot["holdings"][ticker]["close_2025_06_30"] = live[ticker]["close_2025_06_30"]
    snapshot["snapshot_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot.setdefault("provenance", {})["refreshed_from"] = (
        f"yfinance (Yahoo Finance) on {snapshot['snapshot_date']}: history(auto_adjust=False, actions=True) "
        "Dividends column for ex-dates/amounts, raw Close for 2025-06-30"
    )
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {SNAPSHOT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
