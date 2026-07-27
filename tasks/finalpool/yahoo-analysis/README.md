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
   - **Up:** Buy, Outperform, Upgrade, Overweight, Strong Buy, Positive, Accumulate
   - **Flat:** Hold, Neutral, Sector Weight, Perform, Market Perform, Equal Weight, Equal-Weight
   - **Down:** Sell, Underperform, Underweight, Reduce
2. **For Each Rating Event**  
   - Treat the rating timestamp as a calendar date in the stock exchange timezone; ignore its intraday time when matching daily bars.
   - Record the rating date’s closing price and the S&P 500 closing price on that date.  
   - For each horizon (4 mo, 5 mo, 6 mo):
     1. Add the horizon in calendar months, then find the close price exactly on or first after the target date; never use a prior trading day.
     2. Compute the stock’s total return and the S&P 500’s total return over that period.  
     3. Determine if the stock-return direction matches the mapped prediction; the ±2% band applies only to Flat.
     4. Calculate **excess return** = (stock return − S&P 500 return).  
     5. If a required stock or benchmark price is unavailable on or after the rating or horizon date, mark that signal as excluded.
3. **Aggregate Results**  
   - `#Signals` is the total number of rating records released within the two-year window.
   - `#Excluded` is the subset that cannot be evaluated for the given horizon.
   - The included signal count is `#Signals - #Excluded`.
   - Compute **Hit Rate (%)** = 100 × (number of correct predictions ÷ included signal count).
   - Compute **Avg Excess Return (%)** across included signals.
4. **Compare Reliability**
   - Average the three hit rates to get an overall reliability score.
   - The ticker with the higher average hit rate is deemed more reliable.
