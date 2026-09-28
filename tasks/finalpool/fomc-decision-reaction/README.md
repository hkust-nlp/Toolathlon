# FOMC 2025 Decisions and Market Reaction

Task family: **real-data snapshot / live external source**, same shape as
`yahoo-analysis` (agent fills a markdown table from live data, evaluator
recomputes ground truth from the same sources with tolerances) but with a
**web-scraping leg** in front of the Yahoo Finance leg.

## What the agent has to do

1. **Web**: open the Federal Reserve's FOMC calendar
   (`https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`), find
   every *scheduled* meeting under "2025 FOMC Meetings", and open each
   meeting's policy statement to classify the decision (`Hold` / `Cut` / `Hike`)
   and read the new target range for the federal funds rate.
2. **Yahoo Finance**: pull daily closes for `^GSPC` and `^TNX`, then for each
   decision date compute the S&P 500 1-day return (pre-decision close →
   decision-day close), the 5-day return (decision-day close → 5th trading day
   after), and the 10Y yield change in basis points.
3. **Aggregate**: average 1-day return per decision type, the date of the
   largest absolute 1-day move, and the share of decisions where equities and
   yields moved in opposite directions.
4. Fill `results_template.md`, rename to `results.md`.

Expected tool path: `fetch` MCP (`fetch_txt` / `fetch_markdown`) or
`python_execute` + `httpx` for the Fed pages; `yahoo-finance` MCP
(`get_historical_stock_prices`) or `python_execute` + `yfinance` for prices.

## Deliberate traps (all resolved explicitly in `guide.md`)

- **Notation vote**: the 2025 calendar lists an August 22 *notation vote*
  between the July and September meetings. It has a statement link but is not
  a scheduled meeting and must be excluded. Counting it gives 9 rows → fail.
- **Meeting-end date**: meetings span two days ("March 18-19"); the decision
  date is the second day. Using the first day shifts every price lookup by one
  trading day.
- **Fraction parsing**: statements write ranges as "4-1/4 to 4-1/2 percent" and
  "4 to 4-1/4 percent" (note the missing fraction on the lower bound), and use
  a non-breaking hyphen (U+2011) in some places. Must become `4.25-4.50` and
  `4.00-4.25`.
- **Pre-decision close is strictly before**: the "day before" close is the
  previous *trading* day, not the calendar day before. On 2025-03-19 using the
  03-17 close instead of 03-18 changes the 1-day return from 1.08 % to 0.64 %.
- **5-day return is anchored on the decision-day close**, not the pre-decision
  close.
- **`^TNX` is already in percent**; 100 × Δ gives basis points directly.
- The MCP `get_historical_stock_prices` returns dividend-adjusted `Close` by
  default; for index tickers this is identical to the raw close, so no trap
  there — but agents that request `auto_adjust=False` also pass.

## Ground truth (snapshot 2026-09-24, verified live)

| date | decision | range | S&P 1d % | S&P 5d % | 10Y Δbp |
|---|---|---|---|---|---|
| 2025-01-29 | Hold | 4.25-4.50 | -0.47 | 0.37 | 0.40 |
| 2025-03-19 | Hold | 4.25-4.50 | 1.08 | 0.65 | -2.50 |
| 2025-05-07 | Hold | 4.25-4.50 | 0.43 | 4.64 | -3.30 |
| 2025-06-18 | Hold | 4.25-4.50 | -0.03 | 2.68 | 0.40 |
| 2025-07-30 | Hold | 4.25-4.50 | -0.12 | -0.28 | 4.60 |
| 2025-09-17 | Cut | 4.00-4.25 | -0.10 | 0.57 | 5.00 |
| 2025-10-29 | Cut | 3.75-4.00 | -0.00 | -1.37 | 7.50 |
| 2025-12-10 | Cut | 3.50-3.75 | 0.67 | -2.40 | -2.20 |

Hold avg 0.18, Cut avg 0.19, Hike N/A, largest move 2025-03-19, direction
consistency 100.00 %, 8 meetings.

`groundtruth_workspace/gt_snapshot.json` stores only primary facts (decision
date/type/range from the Fed, full-year `^GSPC`/`^TNX` closes); every metric
is derived at grading time so the two legs can't drift in logic.

## How the evaluator grades

`evaluation/main.py` resolves ground truth **live-first** (scrapes the Fed
calendar + statements, pulls yfinance) and falls back to the frozen snapshot
if either source fails or the live decision-date list differs from the
snapshot. Which leg was used is always printed. Set
`TOOLATHLON_FOMC_FORCE_SNAPSHOT=1` for deterministic offline grading.

Checks, in order (first failure exits 1):

- decision-date list equals the eight scheduled meetings exactly;
- per row: decision type exact, target range exact (after normalising
  `4.25 – 4.50`, `4.25%-4.50%` etc.), S&P 1-day / 5-day return within
  ±0.10 pp, yield change within ±0.10 bp;
- per-type averages within ±0.10 pp, `N/A` required for types that did not
  occur; largest-move date exact; direction consistency within ±0.5 pp;
- meeting count and first/last decision dates exact.

## Verification status (2026-09-24)

- Snapshot built from live sources; `build_snapshot.py --check` reports no
  drift on re-run.
- Grader tested with synthetic reports in both snapshot and live modes: the
  correct report passes; counting the notation vote, using the wrong
  pre-decision day, writing the pre-cut range, and a wrong largest-move date
  each fail with the intended message.
- The Fed site occasionally drops TLS mid-handshake (`UNEXPECTED_EOF_WHILE_READING`);
  `_http_get` retries 3× and the snapshot fallback covers a full outage. Agents
  should expect the same and retry.
- No agent rollout has been run yet.

## Local dry run of the grader

```bash
uv run python tasks/finalpool/fomc-decision-reaction/evaluation/main.py \
  --agent_workspace /path/to/workspace \
  --groundtruth_workspace tasks/finalpool/fomc-decision-reaction/groundtruth_workspace

# refresh / diff the snapshot
uv run python tasks/finalpool/fomc-decision-reaction/evaluation/build_snapshot.py --check
```
