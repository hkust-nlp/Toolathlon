#!/usr/bin/env python3
"""Evaluator for ``arxiv-agent-benchmark-audit``.

Task family: real-data snapshot, *live re-parse at evaluation time*.

The agent must locate four LLM-agent benchmark papers on arXiv, record
version-sensitive metadata "as of today", download the latest-version PDFs
and write ``arxiv_audit.json``.  arXiv may receive a new version of any of
these papers at any time, so this grader does NOT compare against a frozen
answer.  Instead it:

1. re-queries arXiv at grading time (metadata API + the abstract page's
   "Submission history"), with retry/backoff for arXiv's ~1 req / 3 s rate
   limit;
2. reconstructs which version was the latest at the agent's launch time
   (``--launch_time``, minus a 24 h safety margin for timezone ambiguity)
   and accepts any version between that one and the live latest, because
   a new version may legitimately appear while the agent is running;
3. verifies that the downloaded file is the genuine arXiv PDF of the
   claimed version by reading the ``arXiv:IDvN [cat] DD Mon YYYY`` stamp
   that arXiv prints in the margin of page 1 (works offline as well);
4. falls back to the checked-in snapshot ``groundtruth_workspace/
   expected_papers.json`` (regenerate it with ``build_snapshot.py``) only
   when arXiv is unreachable after retries.

Immutable facts (arXiv id, v1 date, primary category, first author) are
compared after normalisation; dates get a +/-1 day tolerance to absorb
timezone conversions.  Exit code 0 means pass; any failure prints the
reasons and exits 1.

Standalone: only needs ``arxiv``, ``requests`` and a PDF text extractor
(``pymupdf`` preferred, ``pypdf``/``PyPDF2`` as fallbacks) -- all present in
the Toolathlon environment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

try:  # keep non-ASCII author names printable on any console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(?:v(\d+))?")
STAMP_RE = re.compile(
    r"arXiv:(\d{4}\.\d{4,5})v(\d+)\s*\[([^\]]+)\]\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})"
)
HISTORY_RE = re.compile(
    r"\[v(\d+)\](?:\s*</a>)?(?:\s*</strong>)?\s*"
    r"([A-Z][a-z]{2},\s*\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}\s+\d{2}:\d{2}:\d{2})\s*UTC"
)
REQUIRED_FIELDS = [
    "arxiv_id",
    "title",
    "first_author",
    "num_authors",
    "v1_date",
    "latest_version",
    "latest_version_date",
    "primary_category",
]
DATE_TOLERANCE_DAYS = 1
LAUNCH_MARGIN = timedelta(hours=24)
OFFLINE_EXTRA_VERSIONS = 5  # how many versions newer than the snapshot we accept offline
OFFLINE_ENV = "TOOLATHLON_ARXIV_AUDIT_OFFLINE"  # "1" skips live arXiv calls (air-gapped grading / tests)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36 toolathlon-grader"
)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(msg, flush=True)


def normalize_str(value: Any) -> str:
    return re.sub(r"[^\w]", "", str(value)).lower()


def norm_arxiv_id(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    match = ARXIV_ID_RE.search(str(raw))
    return match.group(1) if match else None


def to_int(raw: Any) -> Optional[int]:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        match = re.fullmatch(r"\s*v?(\d+)\s*", raw)
        if match:
            return int(match.group(1))
    return None


def parse_date_loose(raw: Any) -> Optional[date]:
    if raw is None or isinstance(raw, (int, float, bool)):
        return None
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_launch_time(raw: Any) -> Optional[datetime]:
    """Toolathlon passes ``%Y-%m-%d %H:%M:%S %A``; be lenient anyway."""
    if not raw:
        return None
    text = str(raw).strip().strip('"')
    for fmt in ("%Y-%m-%d %H:%M:%S %A", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    match = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", text)
    if match:
        return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    return None


def dates_close(a: Optional[date], b: Optional[date], tol_days: int = DATE_TOLERANCE_DAYS) -> bool:
    return a is not None and b is not None and abs((a - b).days) <= tol_days


def names_match(expected: str, actual: str) -> bool:
    """Exact after normalisation, or same set of name tokens (handles 'Last, First')."""
    if normalize_str(expected) == normalize_str(actual):
        return True
    tok_e = sorted(normalize_str(t) for t in re.split(r"[\s,]+", expected) if t.strip())
    tok_a = sorted(normalize_str(t) for t in re.split(r"[\s,]+", actual) if t.strip())
    return bool(tok_e) and tok_e == tok_a


def with_retry(fn, label: str, attempts: int = 3, backoffs=(15, 30, 60)):
    last_err: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - any failure is retried
            last_err = exc
            if attempt < attempts:
                delay = backoffs[min(attempt - 1, len(backoffs) - 1)]
                log(
                    f"  [{label}] attempt {attempt}/{attempts} failed "
                    f"({type(exc).__name__}: {str(exc)[:120]}); retrying in {delay}s"
                )
                time.sleep(delay)
    raise RuntimeError(f"{label} failed after {attempts} attempts: {last_err}")


# --------------------------------------------------------------------------- #
# arXiv access (live re-parse)
# --------------------------------------------------------------------------- #
def fetch_api_entry(query_id: str) -> Dict[str, Any]:
    """Metadata of ``query_id`` (bare id -> latest version, ``IDvN`` -> that version)."""
    import arxiv  # arxiv==2.2.0 in the Toolathlon environment

    def _do() -> Dict[str, Any]:
        # delay_seconds is a rate-limit floor between requests; num_retries is
        # the library's own retry budget for 429/5xx/empty pages.
        client = arxiv.Client(delay_seconds=3.0, num_retries=5)
        result = next(client.results(arxiv.Search(id_list=[query_id])))
        match = ARXIV_ID_RE.search(result.entry_id)
        if not match:
            raise ValueError(f"unexpected entry id {result.entry_id}")
        return {
            "arxiv_id": match.group(1),
            "version": int(match.group(2)) if match.group(2) else 1,
            "title": re.sub(r"\s+", " ", result.title).strip(),
            "authors": [a.name for a in result.authors],
            "primary_category": result.primary_category,
            "v1_date": result.published.astimezone(timezone.utc).date(),
            "version_date": result.updated.astimezone(timezone.utc).date(),
        }

    return with_retry(_do, f"arxiv api {query_id}")


def fetch_version_history(arxiv_id: str) -> Dict[int, datetime]:
    """{version: submission datetime (UTC)} parsed from the abstract page."""
    import requests

    def _do() -> Dict[int, datetime]:
        resp = requests.get(
            f"https://arxiv.org/abs/{arxiv_id}",
            headers={"User-Agent": USER_AGENT},
            timeout=(10, 30),
        )
        resp.raise_for_status()
        history: Dict[int, datetime] = {}
        for match in HISTORY_RE.finditer(resp.text):
            stamp = re.sub(r"\s+", " ", match.group(2))
            history[int(match.group(1))] = datetime.strptime(stamp, "%a, %d %b %Y %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        if not history:
            raise ValueError("no submission history found on the abstract page")
        return history

    return with_retry(_do, f"arxiv abs {arxiv_id}")


def fetch_version_history_via_api(arxiv_id: str, latest_version: int) -> Dict[int, datetime]:
    history: Dict[int, datetime] = {}
    for version in range(1, latest_version + 1):
        entry = fetch_api_entry(f"{arxiv_id}v{version}")
        history[version] = datetime.combine(entry["version_date"], datetime.min.time(), tzinfo=timezone.utc)
    return history


# --------------------------------------------------------------------------- #
# PDF verification
# --------------------------------------------------------------------------- #
def first_page_text(path: str) -> Tuple[Optional[str], Optional[int], str]:
    errors: List[str] = []
    try:
        import fitz  # pymupdf

        doc = fitz.open(path)
        pages = doc.page_count
        text = doc[0].get_text() if pages else ""
        return text, pages, "pymupdf"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pymupdf: {exc}")
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(path)
            pages = len(reader.pages)
            text = (reader.pages[0].extract_text() or "") if pages else ""
            return text, pages, module_name
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{module_name}: {exc}")
    log("  could not extract PDF text: " + "; ".join(errors))
    return None, None, "none"


def locate_pdf(workspace: str, arxiv_id: str, version: Optional[int]) -> Tuple[Optional[str], List[str]]:
    notes: List[str] = []
    if version is not None:
        preferred = os.path.join(workspace, "papers", f"{arxiv_id}v{version}.pdf")
        if os.path.isfile(preferred):
            return preferred, notes
    candidates: List[str] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.lower().endswith(".pdf") and arxiv_id in name:
                candidates.append(os.path.join(root, name))
    if version is not None:
        exact = [c for c in candidates if f"{arxiv_id}v{version}" in os.path.basename(c)]
        if exact:
            notes.append(
                f"PDF found at {os.path.relpath(exact[0], workspace)} instead of papers/{arxiv_id}v{version}.pdf"
            )
            return exact[0], notes
    if candidates:
        notes.append(
            f"PDF found at {os.path.relpath(candidates[0], workspace)} without the version in its name; "
            "relying on the arXiv stamp"
        )
        return candidates[0], notes
    return None, notes


def check_pdf(path: str, arxiv_id: str, version: int, title: str, primary_category: Optional[str]):
    """Return (ok, stamp_date, message).  stamp_date is None when no stamp was read."""
    size = os.path.getsize(path)
    if size < 20_000:
        return False, None, f"file is only {size} bytes; not a full paper PDF"
    with open(path, "rb") as handle:
        if not handle.read(5).startswith(b"%PDF"):
            return False, None, "file does not start with %PDF"
    text, pages, engine = first_page_text(path)
    if text is None:
        return False, None, "PDF could not be parsed"
    if pages is not None and pages < 4:
        return False, None, f"PDF has only {pages} page(s)"
    match = STAMP_RE.search(text)
    if match:
        stamp_id = match.group(1)
        stamp_ver = int(match.group(2))
        stamp_cat = match.group(3)
        stamp_date_raw = match.group(4)
        if stamp_id != arxiv_id:
            return False, None, f"arXiv stamp shows {stamp_id}, expected {arxiv_id}"
        if stamp_ver != version:
            return False, None, f"PDF is v{stamp_ver} according to its arXiv stamp, but the audit claims v{version}"
        try:
            stamp_date = datetime.strptime(re.sub(r"\s+", " ", stamp_date_raw), "%d %b %Y").date()
        except ValueError:
            stamp_date = None
        if primary_category and stamp_cat.lower() != primary_category.lower():
            log(f"  note: stamp category {stamp_cat} differs from expected primary category {primary_category}")
        return (
            True,
            stamp_date,
            f"arXiv stamp {stamp_id}v{stamp_ver} [{stamp_cat}] {stamp_date_raw} verified ({engine}, {pages} pages)",
        )
    # No stamp could be read (rare extraction failure): weak title check.
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", title or "")
    norm_text = normalize_str(text)
    hits = sum(1 for w in words if normalize_str(w) in norm_text)
    if words and hits / len(words) >= 0.6:
        return True, None, f"no arXiv stamp readable; title words matched {hits}/{len(words)} (weak check via {engine})"
    total_words = len(words) if words else 0
    return False, None, f"no arXiv stamp readable and title not found on page 1 ({hits}/{total_words} words)"


# --------------------------------------------------------------------------- #
# loading inputs
# --------------------------------------------------------------------------- #
def load_audit(workspace: str) -> Tuple[Optional[List[dict]], str]:
    path = os.path.join(workspace, "arxiv_audit.json")
    if not os.path.isfile(path):
        return None, "arxiv_audit.json not found in the workspace"
    with open(path, encoding="utf-8-sig") as handle:
        raw = handle.read().strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"arxiv_audit.json is not valid JSON: {exc}"
    papers = data.get("papers") if isinstance(data, dict) else data
    if not isinstance(papers, list):
        return None, "arxiv_audit.json must be an object with a top-level 'papers' list"
    if not all(isinstance(p, dict) for p in papers):
        return None, "every entry in 'papers' must be a JSON object"
    return papers, ""


def load_expected(groundtruth_workspace: str) -> Dict[str, Any]:
    path = os.path.join(groundtruth_workspace, "expected_papers.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------- #
# per-paper evaluation
# --------------------------------------------------------------------------- #
def evaluate_paper(
    expected: Dict[str, Any],
    entry: Dict[str, Any],
    workspace: str,
    launch_dt: Optional[datetime],
    now_utc: datetime,
) -> Tuple[List[str], Optional[date]]:
    """Return (errors, v1_date used for the ordering check)."""
    errors: List[str] = []
    arxiv_id = expected["arxiv_id"]

    # --- live metadata -----------------------------------------------------
    live: Optional[Dict[str, Any]] = None
    history: Optional[Dict[int, datetime]] = None
    if os.environ.get(OFFLINE_ENV) == "1":
        log(f"  {OFFLINE_ENV}=1: skipping live arXiv queries, grading against the offline snapshot")
    else:
        try:
            live = fetch_api_entry(arxiv_id)
            log(
                f"  live: v{live['version']} ({live['version_date']}), v1 {live['v1_date']}, "
                f"{len(live['authors'])} authors, {live['primary_category']}"
            )
        except Exception as exc:  # noqa: BLE001
            log(f"  live arXiv metadata unavailable: {exc}")
    if live is not None:
        try:
            history = fetch_version_history(arxiv_id)
        except Exception as exc:  # noqa: BLE001
            log(f"  abstract-page history unavailable ({exc}); trying per-version API queries")
            try:
                history = fetch_version_history_via_api(arxiv_id, live["version"])
            except Exception as exc2:  # noqa: BLE001
                log(f"  per-version API queries failed too: {exc2}")
        if history is not None and live["version"] not in history:
            history[live["version"]] = datetime.combine(
                live["version_date"], datetime.min.time(), tzinfo=timezone.utc
            )

    snapshot_versions = {
        int(k): datetime.fromisoformat(str(v).replace("Z", "+00:00")) for k, v in expected["versions"].items()
    }
    if history is None:
        history = snapshot_versions
        source = "snapshot"
        log(
            f"  using snapshot version history (captured {expected.get('snapshot_date', 'unknown')}): "
            f"{sorted(history)}"
        )
    else:
        source = "live"
        log("  version history (live): " + ", ".join(f"v{k}={history[k].date()}" for k in sorted(history)))

    # --- acceptable versions -------------------------------------------------
    lower_time = (launch_dt - LAUNCH_MARGIN) if launch_dt else (now_utc - timedelta(days=7))
    as_of_launch = max([v for v, t in history.items() if t <= lower_time] or [min(history)])
    if live is not None:
        acceptable = set(range(as_of_launch, live["version"] + 1))
    else:
        acceptable = set(range(as_of_launch, max(history) + OFFLINE_EXTRA_VERSIONS + 1))
    log(f"  acceptable latest_version values: {sorted(acceptable)} (latest as of launch: v{as_of_launch})")

    # --- reference values ------------------------------------------------------
    ref_v1 = live["v1_date"] if live else parse_date_loose(expected["v1_date"])
    ref_category = live["primary_category"] if live else expected["primary_category"]
    title_candidates = {normalize_str(expected["title"])}
    author_candidates = [expected["first_author"]]
    count_candidates = {int(expected["num_authors"])}
    if live is not None:
        title_candidates.add(normalize_str(live["title"]))
        if live["authors"]:
            author_candidates.append(live["authors"][0])
        count_candidates.add(len(live["authors"]))
    ref_title = live["title"] if live else expected["title"]
    first_author_display = author_candidates[-1]

    # --- field checks --------------------------------------------------------------
    claimed_id = norm_arxiv_id(entry.get("arxiv_id"))
    if claimed_id != arxiv_id:
        errors.append(f"arxiv_id mismatch: got {entry.get('arxiv_id')!r}, expected {arxiv_id}")
    elif str(entry.get("arxiv_id", "")).strip() != arxiv_id:
        log(f"  note: arxiv_id written as {entry.get('arxiv_id')!r}; the bare id {arxiv_id} was expected")

    claimed_version = to_int(entry.get("latest_version"))
    if claimed_version is None:
        errors.append(f"latest_version missing or not an integer: {entry.get('latest_version')!r}")
    elif claimed_version not in acceptable:
        errors.append(
            f"latest_version v{claimed_version} is not acceptable; expected one of "
            f"{['v%d' % v for v in sorted(acceptable)]} (history source: {source})"
        )

    # metadata of the claimed version, if it differs from the live latest
    if (
        live is not None
        and claimed_version is not None
        and claimed_version in acceptable
        and claimed_version != live["version"]
    ):
        try:
            claimed_meta = fetch_api_entry(f"{arxiv_id}v{claimed_version}")
            title_candidates.add(normalize_str(claimed_meta["title"]))
            if claimed_meta["authors"]:
                author_candidates.append(claimed_meta["authors"][0])
            count_candidates.add(len(claimed_meta["authors"]))
        except Exception as exc:  # noqa: BLE001
            log(f"  could not fetch metadata of v{claimed_version}: {exc}")

    claimed_vdate = parse_date_loose(entry.get("latest_version_date"))
    ref_vdate = history[claimed_version].date() if claimed_version in history else None
    if claimed_vdate is None:
        errors.append(f"latest_version_date missing or unparseable: {entry.get('latest_version_date')!r}")
    elif ref_vdate is not None and not dates_close(claimed_vdate, ref_vdate):
        errors.append(
            f"latest_version_date {claimed_vdate} does not match v{claimed_version} submitted on {ref_vdate}"
        )

    claimed_v1 = parse_date_loose(entry.get("v1_date"))
    if claimed_v1 is None:
        errors.append(f"v1_date missing or unparseable: {entry.get('v1_date')!r}")
    elif not dates_close(claimed_v1, ref_v1):
        errors.append(f"v1_date {claimed_v1} does not match arXiv v1 submission date {ref_v1}")

    claimed_cat = str(entry.get("primary_category", "")).strip()
    if claimed_cat.lower() != str(ref_category).lower():
        errors.append(f"primary_category {claimed_cat!r} != {ref_category}")

    claimed_title = str(entry.get("title", "")).strip()
    if normalize_str(claimed_title) not in title_candidates:
        errors.append(f"title mismatch: got {claimed_title!r}, expected {ref_title!r}")

    claimed_author = str(entry.get("first_author", "")).strip()
    if not any(names_match(cand, claimed_author) for cand in author_candidates):
        errors.append(f"first_author mismatch: got {claimed_author!r}, expected {first_author_display!r}")

    claimed_count = to_int(entry.get("num_authors"))
    if claimed_count is None or claimed_count not in count_candidates:
        errors.append(f"num_authors {entry.get('num_authors')!r} not in expected values {sorted(count_candidates)}")

    # --- PDF -----------------------------------------------------------------------
    pdf_path, notes = locate_pdf(workspace, arxiv_id, claimed_version)
    for note in notes:
        log(f"  note: {note}")
    if pdf_path is None:
        errors.append(f"downloaded PDF papers/{arxiv_id}v{claimed_version}.pdf not found")
    elif claimed_version is not None:
        ok, stamp_date, message = check_pdf(pdf_path, arxiv_id, claimed_version, ref_title, ref_category)
        log(f"  PDF: {message}")
        if not ok:
            errors.append(f"PDF check failed: {message}")
        else:
            if (
                ref_vdate is None
                and stamp_date is not None
                and claimed_vdate is not None
                and not dates_close(claimed_vdate, stamp_date)
            ):
                errors.append(
                    f"latest_version_date {claimed_vdate} does not match the arXiv stamp date {stamp_date} "
                    f"of v{claimed_version}"
                )
            if source == "snapshot" and claimed_version > max(snapshot_versions) and stamp_date is None:
                errors.append(
                    f"v{claimed_version} is newer than the offline snapshot and the PDF stamp could not confirm it"
                )

    declared_pdf = entry.get("pdf_path")
    if declared_pdf and pdf_path:
        declared_abs = os.path.normpath(os.path.join(workspace, str(declared_pdf)))
        if declared_abs != os.path.normpath(pdf_path):
            log(
                f"  note: pdf_path in JSON ({declared_pdf}) differs from the verified file "
                f"{os.path.relpath(pdf_path, workspace)}"
            )

    return errors, (claimed_v1 or ref_v1)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the arxiv-agent-benchmark-audit task")
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--groundtruth_workspace", required=True)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)
    launch_dt = parse_launch_time(args.launch_time)
    launch_desc = launch_dt.isoformat() if launch_dt else f"unknown ({args.launch_time!r})"
    log(f"launch time: {launch_desc}; grading at {now_utc.isoformat(timespec='seconds')}")

    expected_doc = load_expected(args.groundtruth_workspace)
    expected_papers: List[Dict[str, Any]] = expected_doc["papers"]
    for expected in expected_papers:
        expected.setdefault("snapshot_date", expected_doc.get("snapshot_date", "unknown"))

    papers, err = load_audit(args.agent_workspace)
    if papers is None:
        log(f"FAIL: {err}")
        return 1
    log(f"arxiv_audit.json loaded with {len(papers)} entries")

    failures: List[str] = []
    if len(papers) != len(expected_papers):
        failures.append(f"expected exactly {len(expected_papers)} papers, found {len(papers)}")

    for index, entry in enumerate(papers):
        missing = [k for k in REQUIRED_FIELDS if k not in entry]
        if missing:
            failures.append(f"entry #{index + 1} is missing fields: {missing}")

    by_id: Dict[str, Dict[str, Any]] = {}
    position: Dict[str, int] = {}
    for index, entry in enumerate(papers):
        pid = norm_arxiv_id(entry.get("arxiv_id"))
        if pid is None:
            failures.append(f"entry #{index + 1} has an unparseable arxiv_id: {entry.get('arxiv_id')!r}")
            continue
        if pid in by_id:
            failures.append(f"duplicate entry for arXiv {pid}")
        by_id[pid] = entry
        position[pid] = index
    unexpected = sorted(set(by_id) - {p["arxiv_id"] for p in expected_papers})
    if unexpected:
        failures.append(f"unexpected papers in the audit: {unexpected}")

    file_order_v1: List[Tuple[int, date]] = []
    for expected in expected_papers:
        arxiv_id = expected["arxiv_id"]
        log(f"\n=== {expected.get('key', arxiv_id)} ({arxiv_id}) ===")
        entry = by_id.get(arxiv_id)
        if entry is None:
            failures.append(f"paper {arxiv_id} ({expected.get('key')}) is missing from the audit")
            continue
        errors, v1_used = evaluate_paper(expected, entry, args.agent_workspace, launch_dt, now_utc)
        if errors:
            for e in errors:
                log(f"  ERROR: {e}")
            failures.extend(f"{arxiv_id}: {e}" for e in errors)
        else:
            log("  OK")
        if v1_used is not None:
            file_order_v1.append((position[arxiv_id], v1_used))

    # ordering: entries must appear sorted by v1_date ascending
    if len(file_order_v1) == len(expected_papers):
        in_file_order = [d for _, d in sorted(file_order_v1)]
        if in_file_order != sorted(in_file_order):
            failures.append(
                f"papers are not sorted by v1_date ascending (file order: {[str(d) for d in in_file_order]})"
            )

    log("")
    if failures:
        log("EVALUATION FAILED:")
        for f in failures:
            log(f"  - {f}")
        return 1
    log("All checks passed: arxiv_audit.json is complete, version-consistent with arXiv, and the PDFs are genuine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
