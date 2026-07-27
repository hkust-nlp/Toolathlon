## Requirements
- **Stock Tickers**: NVDA, AAPL
- **Time Horizons**: 4 months, 5 months, 6 months
- **Ratings Source**: Use every row from `yfinance.Ticker(ticker).upgrades_downgrades` whose exchange-local calendar date falls within the inclusive two-year window. Use `ToGrade` as the rating and count every row as one signal.
- **Rating Direction Mapping**:
  - Buy / Outperform / Upgrade / Overweight / Strong Buy / Positive / Accumulate → Predict Up
  - Hold / Neutral / Sector Weight / Perform / Market Perform / Equal Weight / Equal-Weight → Predict Flat (within ±2% considered a hit)
  - Sell / Underperform / Underweight / Reduce → Predict Down
- **Benchmark Index**: S&P 500 (^GSPC), used to calculate excess returns
- **Price Date Matching**: Treat each analyst-rating timestamp as a calendar date in the stock exchange timezone. Add 4, 5, or 6 calendar months to obtain each horizon target date. For both the rating date and target date, use that date's close or the first available trading day's close after it; never use a prior trading day.
- **Hit Direction**: Predict Up is a hit when the stock return is greater than 0; Predict Down is a hit when it is less than 0; the ±2% band applies only to Predict Flat. Use stock return—not excess return—to determine a hit.

# Expected Outputs
1. Update the table in the provided file with calculated values, maintaining the exact structure

| Ticker | Horizon | Hit Rate (%) | Avg Excess Return (%) | #Signals | #Excluded |
|--------|---------|--------------|-----------------------|----------|-----------|
Columns:
   - **Ticker**: Stock symbol (NVDA or AAPL)
   - **Horizon**: Time window (4 months, 5 months, 6 months)
   - **Hit Rate (%)**: Percentage of included ratings where the predicted direction matches actual price movement
   - **Avg Excess Return (%)**: Average stock return minus S&P 500 return over the horizon across included ratings
   - **#Signals**: Count of all rating records released within the past two years.
   - **#Excluded**: Count of those signals excluded because the required stock or benchmark price is unavailable on or after the rating or horizon date.
   - **Included signal count**: `#Signals - #Excluded`. Use this count as the denominator for Hit Rate and Avg Excess Return.

2. Update the "More Reliable" section in with:
- **Choice**: Specify the stock (NVDA or AAPL) with the higher arithmetic mean Hit Rate across the three horizons.
- **Conclusion**: A brief paragraph comparing Hit Rate and Avg Excess Return for NVDA and AAPL across the three horizons. Highlight which stock’s ratings are more reliable and note any significant differences.

3. Update the "Data Range" section with:
- **Start** (should be two years ago)
- **End** (should be the current date)

# Other
- Make sure saving your results in `results.md`, which will later be used for evaluation.
- Round numerical results (Hit Rate, Avg Excess Return) to 2 decimal places for consistency.
