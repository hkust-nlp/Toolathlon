- **Data**: Fetch monthly data for WTI (CL=F) and Brent (BZ=F) from Yahoo Finance for the last 12 complete calendar months. Prices should be rounded to 4 decimal places, percentages to 2 decimal places.
- **Calculations**:

  | Indicator        | Description                                                                                                                                |
  | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
  | Brent-WTI Spread | Brent Close - WTI Close                                                                                                                    |
  | MoM%             | (Current Month / Previous Month - 1) × 100%                                                                                                |
  | Z-Score(6m)      | Standardized using mean and SAMPLE standard deviation (ddof=1) of the last 6 spreads (z=0 when sample < 4 or std = 0, clipped to [-3,3]).  |

- **Backtest Strategy**: Generate signals based on z-score (z ≤ -1: long spread = long Brent + short WTI; z ≥ +1: short spread = short Brent + long WTI; otherwise flat). Signals generated at month-end, held for 1 month, closed at next month-end. Only one position at a time; equal weight for both legs; 0.40% round-trip cost included in monthly net returns. Calculate total return, annualized return, Sharpe ratio, win rate, and maximum drawdown.

  - **Tip:** Entry Month refers to signal generation month, Exit Month refers to position closing month. Position returns are calculated from signal generation month to position closing month (spanning 2 calendar months)

- **Write results to** **`Oil Market Summary`** **Oil Market Summary** and **`Spread Strategy Backtest`** **Spread Strategy Backtest** data tables. For `Spread Strategy Backtest`, update the unique "Metric" row and add/update corresponding "Trade" rows for each executed trade:

  - When Type=Metric: fill in `Period Start`, `Period End`, `Trades`, `Total Return %`, `Annualized Return %`, `Sharpe (ann.)`, `Win Rate %`, `Max Drawdown %`, `Cost Assumption`;
  - When Type=Trade: fill in `Entry Month`, `Exit Month`, `Signal`, `Entry Spread`, `Exit Spread`, `Leg Returns %`, `Net PnL %`, `Notes`.
