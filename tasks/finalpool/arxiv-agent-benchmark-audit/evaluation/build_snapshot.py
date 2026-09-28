#!/usr/bin/env python3
"""(Re)build ``groundtruth_workspace/expected_papers.json`` from live arXiv data.

The evaluator (``main.py``) re-parses arXiv at grading time and only uses this
snapshot as an offline fallback, so refreshing it is optional.  Run it from
the repository root whenever you want the fallback to reflect the current
arXiv state::

    uv run python tasks/finalpool/arxiv-agent-benchmark-audit/evaluation/build_snapshot.py

Immutable identity facts (arXiv ids and the search clues) live in
``PAPERS`` below; everything else is fetched.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from main import fetch_api_entry, fetch_version_history  # noqa: E402

PAPERS = [
    {"key": "webarena", "arxiv_id": "2307.13854", "clue": "original WebArena paper, July 2023"},
    {"key": "swe-bench", "arxiv_id": "2310.06770", "clue": "original SWE-bench paper, October 2023"},
    {"key": "gaia", "arxiv_id": "2311.12983", "clue": "GAIA benchmark for general AI assistants, November 2023"},
    {"key": "toolathlon", "arxiv_id": "2510.25726", "clue": "The Tool Decathlon (Toolathlon), October 2025"},
]

OUTPUT = os.path.join(os.path.dirname(HERE), "groundtruth_workspace", "expected_papers.json")


def main() -> int:
    snapshot = {
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "arxiv.org metadata API (export.arxiv.org) and abstract-page submission history",
        "note": "Offline fallback only; the evaluator re-queries arXiv live at grading time.",
        "papers": [],
    }
    for paper in PAPERS:
        arxiv_id = paper["arxiv_id"]
        print(f"fetching {arxiv_id} ({paper['key']}) ...", flush=True)
        meta = fetch_api_entry(arxiv_id)
        history = fetch_version_history(arxiv_id)
        history.setdefault(meta["version"], datetime.combine(meta["version_date"], datetime.min.time(), tzinfo=timezone.utc))
        snapshot["papers"].append(
            {
                "key": paper["key"],
                "clue": paper["clue"],
                "arxiv_id": arxiv_id,
                "title": meta["title"],
                "first_author": meta["authors"][0],
                "num_authors": len(meta["authors"]),
                "primary_category": meta["primary_category"],
                "v1_date": meta["v1_date"].isoformat(),
                "latest_version_at_snapshot": meta["version"],
                "latest_version_date_at_snapshot": meta["version_date"].isoformat(),
                "versions": {str(v): history[v].strftime("%Y-%m-%dT%H:%M:%SZ") for v in sorted(history)},
            }
        )
        print(f"  v{meta['version']} ({meta['version_date']}), {len(meta['authors'])} authors, versions {sorted(history)}")
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
