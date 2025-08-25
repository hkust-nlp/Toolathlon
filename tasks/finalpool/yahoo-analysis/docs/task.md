# Task
Evaluate the accuracy of historical analyst ratings for NVIDIA (NVDA) and Apple (AAPL) based on subsequent stock price performance over 4, 5, and 6-month time horizons. Use data from the past two years up to the present.

Save your results in the `results_template.md` file in the workspace, following its specified format. Once completed, **rename the file to `results.md`**

## Requirements
- **Stock Tickers**: NVDA, AAPL
- **Time Horizons**: 4 months, 5 months, 6 months
- **Rating Direction Mapping**:
  - Buy / Outperform / Upgrade / Overweight / Strong Buy / Positive / Accumulate → Predict Up
  - Hold / Neutral / Sector Weight / Perform / Market Perform / Equal Weight → Predict Flat (within ±2% considered a hit)
  - Sell / Underperform / Underweight → Predict Down
- **Benchmark Index**: S&P 500 (^GSPC), used to calculate excess returns

## Expected Outputs
1. Update the table in the provided file with calculated values, maintaining the exact structure

| Ticker | Horizon | Hit Rate (%) | Avg Excess Return (%) | #Signals | #Excluded |
|--------|---------|--------------|-----------------------|----------|-----------|
Columns:
   - **Ticker**: Stock symbol (NVDA or AAPL)
   - **Horizon**: Time window (4 months, 5 months, 6 months)
   - **Hit Rate (%)**: Percentage of ratings where the predicted direction matches actual price movement
   - **Avg Excess Return (%)**: Average stock return minus S&P 500 return over the horizon
   - **#Signals**: Number of valid rating signals used
   - **#Excluded**: Number of signals excluded because the specified horizon falls outside the available historical price data.

2. Update the "More Reliable" section in with:
- **Choice**: Specify which stock (NVDA or AAPL) has more reliable analyst ratings.
- **Conclusion**: A brief paragraph comparing Hit Rate and Avg Excess Return for NVDA and AAPL across the three horizons. Highlight which stock’s ratings are more reliable and note any significant differences.

3. Update the "Data Range" section with:
- **Start** (should be two years ago)
- **End** (should be the current date)

## Other
You can create other helper files, but make sure saving your results in `results.md`, which will later be used for evaluation.
Round numerical results (Hit Rate, Avg Excess Return) to 2 decimal places for consistency.