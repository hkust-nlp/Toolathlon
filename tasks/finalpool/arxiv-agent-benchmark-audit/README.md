# arxiv-agent-benchmark-audit

Task family: **real-data snapshot / live external source** (same family as
`find-alita-paper`, `nvidia-stock-analysis`, `ipad-edu-price`).
Sub-mode: **live re-parse at evaluation time**.

## What the agent has to do

Starting from four vague clues, find the original WebArena, SWE-bench, GAIA and
Tool Decathlon papers on arXiv, record version-sensitive metadata *as of
today* (latest version number and date, author count, title of the latest
version, v1 date, primary category), download the latest-version PDFs into
`papers/{arxiv_id}v{N}.pdf`, and write `arxiv_audit.json` sorted by v1 date.
The only initial file is `audit_spec.md` (the JSON schema).

Expected tool path: `scholarly` / `arxiv_local` for search, `fetch` for the
arXiv abstract page or API, `terminal` (`curl`/`wget`) for the PDFs,
`filesystem` for the JSON.

## Why it is a "real data snapshot" task

The answer is not fixed: arXiv may receive a new version of any of the four
papers at any time, which changes `latest_version`, `latest_version_date`,
possibly `title` and `num_authors`, and the PDF that must be downloaded.
Instead of freezing an answer, the grader re-derives it from arXiv when it
runs.

## How the evaluator grades

`evaluation/main.py` (standalone; needs `arxiv`, `requests`, `pymupdf` or
`pypdf`/`PyPDF2`, all in the Toolathlon environment):

1. **Live re-parse.** Queries the arXiv API for each paper (latest version,
   title, authors, v1 date, primary category) and parses the abstract page's
   "Submission history" to get the date of every version. All arXiv calls use
   retry with backoff (arXiv allows about one request every 3 seconds).
2. **Launch-time window.** With `--launch_time` it reconstructs which version
   was the latest when the agent started (minus a 24 h margin for timezone
   ambiguity) and accepts any `latest_version` from that one up to the live
   latest, so a version posted mid-run cannot fail a correct agent.
3. **Genuine PDF.** Reads the `arXiv:IDvN [cat] DD Mon YYYY` stamp printed on
   page 1 of every arXiv PDF and requires `N` to equal the claimed version.
   This proves the file is the real arXiv PDF of that version and works even
   when arXiv is unreachable at grading time.
4. **Tolerances.** Dates: ±1 day (timezone conversions). Strings: compared
   after removing punctuation/whitespace and lower-casing; author names also
   match on token sets ("Last, First"). `arxiv_id` accepts URLs or `vN`
   suffixes but must resolve to the right id.
5. **Offline fallback.** If arXiv cannot be reached after retries (or
   `TOOLATHLON_ARXIV_AUDIT_OFFLINE=1` is set), the grader uses
   `groundtruth_workspace/expected_papers.json` (snapshot date recorded
   inside). Versions newer than the snapshot are then accepted only if the PDF
   stamp confirms them.

The final chat reply (four titles) is requested in the prompt but is not
graded; the JSON file and PDFs are the deliverables.

## Verification status

Verified on 2026-09-22 with real arXiv data: a correct workspace (four
version-matching PDFs downloaded from arxiv.org) passes in both online and
offline mode; a workspace with a stale version + mismatching PDF, a wrong
first author, unsorted entries and a missing PDF fails with one message per
defect. No agent run has been performed yet; run it on the evaluation server
with the usual `run_single_containerized.sh finalpool/arxiv-agent-benchmark-audit ...`.

## Refreshing the offline snapshot

```bash
uv run python tasks/finalpool/arxiv-agent-benchmark-audit/evaluation/build_snapshot.py
```

## Local dry run of the grader

```bash
uv run python tasks/finalpool/arxiv-agent-benchmark-audit/evaluation/main.py \
  --agent_workspace /path/to/workspace \
  --groundtruth_workspace tasks/finalpool/arxiv-agent-benchmark-audit/groundtruth_workspace \
  --launch_time "2026-09-22 10:00:00 Tuesday"
```
