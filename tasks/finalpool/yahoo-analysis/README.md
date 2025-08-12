# NVDA & AAPL Analyst Ratings Evaluation

This task measures the accuracy of historical analyst ratings for NVIDIA (NVDA) and Apple (AAPL) by comparing predicted directions against actual stock performance over 4-, 5-, and 6-month horizons. Results will be saved in `results.md` using the provided template.

## Tools
- **Yahoo Finance MCP Server**
- **Python**

## Data Range
- **Start:** Two years before today  
- **End:** Today’s date

## Data Collection
1. **Price History**
   - Fetch daily close prices for NVDA, AAPL, and S&P 500 (`^GSPC`) from two years ago to today.
2. **Analyst Ratings**
   - Use `Ticker.upgrades_downgrades` to retrieve all rating events for NVDA and AAPL in the same two-year window.

## Processing Steps
1. **Map Rating to Prediction**  
   - **Up:**
   - **Flat:** 
   - **Down:**
2. **For Each Rating Event**  
   - Record the rating date’s closing price and the S&P 500 closing price on that date.  
   - For each horizon (4 mo, 5 mo, 6 mo):
     1. Find the close price exactly or closest after the rating date + horizon.  
     2. Compute the stock’s total return and the S&P 500’s total return over that period.  
     3. Determine if the sign/direction matches the mapped prediction.  
     4. Calculate **excess return** = (stock return − S&P 500 return).  
     5. If the target date is in the future (beyond today), mark that signal as excluded.
3. **Aggregate Results**  
   - Count total valid signals (`#Signals`) and excluded signals (`#Excluded`) per ticker & horizon.  
   - Compute **Hit Rate (%)** = 100 × (number of correct predictions ÷ #Signals).  
   - Compute **Avg Excess Return (%)** across all valid signals.
4. **Compare Reliability**
   - Average the three hit rates to get an overall reliability score.
   - The ticker with the higher average hit rate is deemed more reliable.
