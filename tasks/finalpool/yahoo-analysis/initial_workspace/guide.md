## Requirements
- **Stock Tickers**: NVDA, AAPL
- **Time Horizons**: 4 months, 5 months, 6 months
- **Rating Direction Mapping**:
  - Buy / Outperform / Upgrade / Overweight / Strong Buy / Positive / Accumulate → Predict Up
  - Hold / Neutral / Sector Weight / Perform / Market Perform / Equal Weight → Predict Flat (within ±2% considered a hit)
  - Sell / Underperform / Underweight → Predict Down
- **Benchmark Index**: S&P 500 (^GSPC), used to calculate excess returns

# Expected Outputs
1. Update the table in the provided file with calculated values, maintaining the exact structure

| Ticker | Horizon | Hit Rate (%) | Avg Excess Return (%) | #Signals | #Excluded |
|--------|---------|--------------|-----------------------|----------|-----------|
Columns:
   - **Ticker**: Stock symbol (NVDA or AAPL)
   - **Horizon**: Time window (4 months, 5 months, 6 months)
   - **Hit Rate (%)**: Percentage of ratings where the predicted direction matches actual price movement
   - **Avg Excess Return (%)**: Average stock return minus S&P 500 return over the horizon
   - **#Signals**: Count of valid rating signals, i.e., all ratings records released within the past two years.
   - **#Excluded**: Count of signals excluded because the specified horizon exceeds available historical price data—for example, if the price on the rating release date or after the desired period is unavailable.

2. Update the "More Reliable" section in with:
- **Choice**: Specify which stock (NVDA or AAPL) has more reliable analyst ratings.
- **Conclusion**: A brief paragraph comparing Hit Rate and Avg Excess Return for NVDA and AAPL across the three horizons. Highlight which stock’s ratings are more reliable and note any significant differences.

3. Update the "Data Range" section with:
- **Start** (should be two years ago)
- **End** (should be the current date)

# Other
- Make sure saving your results in `results.md`, which will later be used for evaluation.
- Round numerical results (Hit Rate, Avg Excess Return) to 2 decimal places for consistency.