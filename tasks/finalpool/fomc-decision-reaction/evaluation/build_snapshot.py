#!/usr/bin/env python3
"""Build or check ``groundtruth_workspace/gt_snapshot.json`` for ``fomc-decision-reaction``.

    uv run python tasks/finalpool/fomc-decision-reaction/evaluation/build_snapshot.py          # rewrite
    uv run python tasks/finalpool/fomc-decision-reaction/evaluation/build_snapshot.py --check  # diff only

The snapshot stores primary facts only (decision dates/types/ranges from the Fed
website, and the full-year ``^GSPC`` / ``^TNX`` daily closes); every metric is
derived at grading time by ``main.py``.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import SP500, TNX, YEAR, derive_expected, fetch_closes, scrape_fed_decisions  # noqa: E402

SNAPSHOT = Path(__file__).resolve().parent.parent / "groundtruth_workspace" / "gt_snapshot.json"


def build() -> dict:
    return {
        "snapshot_date": date.today().isoformat(),
        "sources": {
            "decisions": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm + policy statements",
            "prices": f"yfinance {SP500} / {TNX} daily Close, auto_adjust=False",
        },
        "decisions": scrape_fed_decisions(),
        "sp500_close": fetch_closes(SP500, f"{YEAR}-01-01", f"{YEAR + 1}-02-01"),
        "tnx_close": fetch_closes(TNX, f"{YEAR}-01-01", f"{YEAR + 1}-02-01"),
    }


def main() -> int:
    live = build()
    exp = derive_expected(live)
    print(f"{'date':12s} {'decision':8s} {'range':12s} {'ret1%':>7s} {'ret5%':>7s} {'bp':>7s}")
    for r in exp["rows"]:
        print(f"{r['date']:12s} {r['decision']:8s} {r['range']:12s} {r['ret1']:7.2f} {r['ret5']:7.2f} {r['bp']:7.2f}")
    print(f"averages={ {k: round(v, 2) for k, v in exp['averages'].items()} } largest={exp['largest']} "
          f"consistency={exp['consistency']:.2f} count={exp['count']}")

    if "--check" in sys.argv:
        if not SNAPSHOT.exists():
            print(f"no snapshot at {SNAPSHOT}")
            return 1
        old = derive_expected(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
        diffs = []
        if [r["date"] for r in old["rows"]] != [r["date"] for r in exp["rows"]]:
            diffs.append("decision dates differ")
        for o, n in zip(old["rows"], exp["rows"]):
            for k in ("decision", "range"):
                if o[k] != n[k]:
                    diffs.append(f"{n['date']} {k}: {o[k]} -> {n[k]}")
            for k in ("ret1", "ret5", "bp"):
                if abs(o[k] - n[k]) > 0.01:
                    diffs.append(f"{n['date']} {k}: {o[k]:.2f} -> {n[k]:.2f}")
        print("snapshot check:", "OK, no drift" if not diffs else "\n  ".join(["DRIFT"] + diffs))
        return 1 if diffs else 0

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(live, indent=1), encoding="utf-8")
    print(f"wrote {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
