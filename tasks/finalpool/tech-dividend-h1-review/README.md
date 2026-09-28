# tech-dividend-h1-review

Task family: **real-data snapshot / live external source** (same family as
`nvidia-stock-analysis`, `find-alita-paper`, `ipad-edu-price`).
Sub-mode: **fixed date window, frozen snapshot with tolerances**.

## What the agent has to do

Review the 2025 H1 dividend income of a six-stock Nasdaq portfolio (MSFT 40,
AAPL 150, CSCO 250, PEP 60, COST 25, TXN 50 shares) from Yahoo Finance data:
list every dividend whose **ex-dividend date** falls in 2025-01-01 .. 2025-06-30,
compute per-share totals, cash received, the 2025-06-30 close, half-year
yield and income share per stock, plus the portfolio total, the best-yield
stock and the largest cash contributor, and write `dividend_review.json`.
The only initial file is `report_spec.md` (schema, definitions, rounding).

Expected tool path: `yahoo-finance` MCP (`get_historical_stock_prices` with the
`Dividends` column or `get_stock_actions`, `get_stock_price_by_date`) or
`python_execute` with `yfinance`, then `filesystem` for the JSON.

Deliberate traps that the prompt resolves explicitly:

- PEP went ex-dividend on 2024-12-06 but paid on 2025-01-06 (outside the
  window by ex-date; must be excluded). PEP's 2025-06-06 ex-date paid on
  2025-06-30 (inside).
- CSCO's 2025-01-03 ex-date is inside; 2025-07-03 is outside. TXN's
  2025-07-31 is outside.
- The best-yield stock (PEP) differs from the largest cash contributor
  (CSCO, because of its 250 shares), so both summary fields are informative.

## Ground truth

`groundtruth_workspace/gt_snapshot.json` (snapshot date 2026-09-22) stores
only primary facts: ex-dates and cash per share, and the regular closing price
on 2025-06-30. The evaluator derives everything else from it.

| ticker | ex-dates and amounts (USD/share) | 2025-06-30 close |
|---|---|---|
| MSFT | 2025-02-20 0.83, 2025-05-15 0.83 | 497.41 |
| AAPL | 2025-02-10 0.25, 2025-05-12 0.26 | 205.17 |
| CSCO | 2025-01-03 0.40, 2025-04-03 0.41 | 69.38 |
| PEP | 2025-03-07 1.355, 2025-06-06 1.4225 | 132.04 |
| COST | 2025-02-07 1.16, 2025-05-02 1.30 | 989.94 |
| TXN | 2025-01-31 1.36, 2025-04-30 1.36 | 207.62 |

Derived: total cash 709.55; highest half-year yield PEP (2.10 %); largest cash
contributor CSCO (202.50).

Provenance: dividends from the Nasdaq dividend-history API; closes cross-checked
between the Nasdaq chart API and East Money daily quotes (both agree to the
cent). The authoring machine could not reach Yahoo Finance, so the yfinance
path has not been executed yet. **Before the first formal run, execute on the
evaluation server:**

```bash
uv run python tasks/finalpool/tech-dividend-h1-review/evaluation/build_snapshot.py --check
```

It prints yfinance's ex-dates/amounts/closes next to the snapshot and exits 1
if anything differs (drop `--check` to rewrite the snapshot from yfinance).

## How the evaluator grades

`evaluation/main.py` is standalone (stdlib only) and checks `dividend_review.json`:

- period start/end equal 2025-01-01 / 2025-06-30;
- exactly the six tickers, correct share counts, `payments_count`;
- dividends matched one-to-one: ex-date ±1 day, amount within 0.5 % (so
  `1.4225` vs `1.42` passes, a missing or extra payment fails);
- `dividend_per_share_total` 0.5 %, `cash_received` 0.5 %,
  `total_cash_received` 0.5 % (absolute floors 0.006 / 0.06 / 0.10);
- `close_2025_06_30` within 5 % (Yahoo's default dividend-adjusted Close is
  about 0.3–1.5 % below the regular Close); `h1_yield_pct` within 6 % relative
  or 0.02 points; `income_share_pct` within 0.15 points;
- `highest_h1_yield_ticker` == PEP, `largest_cash_contributor_ticker` == CSCO.

Holdings order is reported but not penalised. Numbers given as strings with
`$`/`%` are parsed. Set `TOOLATHLON_DIVIDEND_LIVE_CHECK=1` to print a live
yfinance drift report next to the verdict (informational only).

## Verification status

Evaluator verified on 2026-09-22 with synthetic reports: a correct report
passes (also with Yahoo-style dividend-adjusted closes and with `$`/`%`
formatted strings); counting PEP's 2024-12-06 ex-date, or a close 10 % off,
fails with the expected messages. The yfinance consistency check
(`build_snapshot.py --check`) still has to be run on the server, and no agent
run has been performed yet.

## Local dry run of the grader

```bash
uv run python tasks/finalpool/tech-dividend-h1-review/evaluation/main.py \
  --agent_workspace /path/to/workspace \
  --groundtruth_workspace tasks/finalpool/tech-dividend-h1-review/groundtruth_workspace
```
