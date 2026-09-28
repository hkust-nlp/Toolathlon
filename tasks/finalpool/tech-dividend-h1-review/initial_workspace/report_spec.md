# dividend_review.json specification

Write a single JSON object to `dividend_review.json` in the workspace root. Do not wrap it in markdown code fences. All numbers must be JSON numbers (not strings), without currency symbols or percent signs.

## Definitions

- **Window**: a dividend counts only if its **ex-dividend date** is between `2025-01-01` and `2025-06-30` inclusive. Payment dates and record dates are irrelevant.
- **Data source**: Yahoo Finance (for example the historical price data that includes a `Dividends` column, or the stock actions history).
- **Closing price**: the regular closing price on 2025-06-30. If your data source only provides split/dividend-adjusted closes, use that value; small differences are tolerated.
- `dividend_per_share_total` = sum of the cash dividends per share in the window.
- `cash_received` = `dividend_per_share_total` × shares held.
- `h1_yield_pct` = `dividend_per_share_total` ÷ `close_2025_06_30` × 100.
- `income_share_pct` = `cash_received` ÷ `total_cash_received` × 100.
- `total_cash_received` = sum of `cash_received` over the six stocks.

## Rounding

- `amount_per_share` and `dividend_per_share_total`: up to 4 decimal places (do not round away real precision, e.g. keep `1.4225`).
- `cash_received`, `close_2025_06_30`, `total_cash_received`: 2 decimal places.
- `h1_yield_pct`, `income_share_pct`: 2 decimal places.

## Schema

```json
{
  "period": {"start": "2025-01-01", "end": "2025-06-30"},
  "holdings": [
    {
      "ticker": "MSFT",
      "shares": 40,
      "dividends": [
        {"ex_date": "YYYY-MM-DD", "amount_per_share": 0.0}
      ],
      "payments_count": 0,
      "dividend_per_share_total": 0.0,
      "cash_received": 0.0,
      "close_2025_06_30": 0.0,
      "h1_yield_pct": 0.0,
      "income_share_pct": 0.0
    }
  ],
  "total_cash_received": 0.0,
  "highest_h1_yield_ticker": "TICKER",
  "largest_cash_contributor_ticker": "TICKER"
}
```

Rules:

- `holdings` must contain exactly six objects, one per ticker, in the order MSFT, AAPL, CSCO, PEP, COST, TXN.
- `ticker` values are upper-case symbols; `shares` are the integers given in the task.
- `dividends` lists the payments in the window in chronological order; `payments_count` equals its length.
- Dates use the format `YYYY-MM-DD`.
- `highest_h1_yield_ticker` and `largest_cash_contributor_ticker` are tickers from the portfolio.
