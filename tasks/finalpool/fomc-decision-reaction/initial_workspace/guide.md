## Requirements
- **Decision Source**: The Federal Reserve's FOMC calendar page, `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`. Use every **scheduled** meeting listed under "2025 FOMC Meetings". The decision date is the **last day** of the meeting (the day the policy statement is released). Exclude any entry that is not a scheduled meeting, such as a notation vote or an unscheduled meeting.
- **Decision Type**: Read each meeting's policy statement (the "Statement" HTML link on the calendar page; statements live at `https://www.federalreserve.gov/newsevents/pressreleases/monetaryYYYYMMDDa.htm`). Classify the decision by what the Committee decided about the target range for the federal funds rate:
  - `Hold` — the Committee decided to **maintain** the target range
  - `Cut` — the Committee decided to **lower** the target range
  - `Hike` — the Committee decided to **raise** the target range
- **Target Range**: Record the target range for the federal funds rate that applies **after** the decision, as two decimal percentages, e.g. `4.25-4.50`. Fractions in the statement such as "4-1/4 to 4-1/2 percent" must be converted to decimals.
- **Market Data Source**: Yahoo Finance daily closes for the S&P 500 index (`^GSPC`) and the CBOE 10-Year Treasury Note Yield index (`^TNX`). Use the `Close` column. `^TNX` is quoted in percent (e.g. `4.551` means 4.551 %).
- **Price Date Matching**:
  - **Pre-decision close**: the last trading day's close **strictly before** the decision date.
  - **Decision-day close**: the close on the decision date itself, or the first trading day after it if the decision date is not a trading day.
  - **Five-day close**: the close exactly **5 trading days** after the decision-day close (i.e. the fifth trading-day bar after the decision-day bar).
- **Metrics per decision**:
  - **S&P 1-Day Return (%)** = 100 × (decision-day close ÷ pre-decision close − 1)
  - **S&P 5-Day Return (%)** = 100 × (five-day close ÷ decision-day close − 1)
  - **10Y Yield Change (bp)** = 100 × (decision-day `^TNX` close − pre-decision `^TNX` close), in basis points. A positive value means the yield rose.
- **Summary**:
  - **Average 1-Day Return by Decision Type**: for each decision type that occurred in 2025, the arithmetic mean of the S&P 1-Day Return across that type's decisions.
  - **Largest 1-Day Move**: the decision date whose S&P 1-Day Return has the largest absolute value.
  - **Direction Consistency (%)**: 100 × (number of decisions where the S&P 1-Day Return and the 10Y Yield Change have opposite signs ÷ total decisions). A zero value for either metric counts as not opposite.

# Expected Outputs
1. Update the table in the provided file with calculated values, maintaining the exact structure, one row per scheduled 2025 meeting in chronological order:

| Decision Date | Decision | Target Range (%) | S&P 1-Day Return (%) | S&P 5-Day Return (%) | 10Y Yield Change (bp) |
|---------------|----------|------------------|----------------------|----------------------|-----------------------|

Columns:
   - **Decision Date**: `YYYY-MM-DD`, the last day of the meeting
   - **Decision**: `Hold`, `Cut`, or `Hike`
   - **Target Range (%)**: lower-upper bound after the decision, e.g. `4.25-4.50`
   - **S&P 1-Day Return (%)**, **S&P 5-Day Return (%)**: as defined above
   - **10Y Yield Change (bp)**: as defined above

2. Update the "Summary" section with:
- **Hold Avg 1-Day Return (%)**, **Cut Avg 1-Day Return (%)**, **Hike Avg 1-Day Return (%)**: the per-type averages. Write `N/A` for a decision type that did not occur in 2025.
- **Largest 1-Day Move**: the decision date (`YYYY-MM-DD`) with the largest absolute S&P 1-Day Return
- **Direction Consistency (%)**: as defined above
- **Conclusion**: a brief paragraph on whether equity and bond markets reacted differently to holds versus cuts in 2025, citing the numbers above.

3. Update the "Data Range" section with:
- **Meetings**: the number of scheduled 2025 meetings included
- **First Decision** / **Last Decision**: the first and last decision dates included (`YYYY-MM-DD`)

# Other
- Make sure saving your results in `results.md`, which will later be used for evaluation.
- Round all percentages and basis-point values to 2 decimal places.
- Do not use the closing price of a trading day **before** the decision date as the decision-day close.
