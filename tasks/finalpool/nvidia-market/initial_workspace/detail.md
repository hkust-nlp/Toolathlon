# Sheet 1: "Basic Info & Holding Trend"

* **Rows**: Each row represents one quarter from 2023 Q1 through 2024 Q4.
* **Columns**:

  1. **Quarter**: Label of the quarter (e.g., "2023 Q1").
  2. **NVDA End-of-Quarter Stock Price (USD)**: NVDA closing price at quarter end.
  3. **Outstanding Shares (Million Shares)**: Outstanding total shares in millions.
  4. **Market Cap (Billion USD)**: Total market capitalization in billion USD.
  5. **Top 20 Shareholders Total Holding Ratio (%)**: Combined Top 20 institutions' holding as percentage of total outstanding shares.
  6. **Top 10 Shareholders Total Holding Ratio (%)**: Combined Top 10 institutions' holding percentage.
  7. **Top 5 Shareholders Total Holding Ratio (%)**: Combined Top 5 institutions' holding percentage.
  8. **Top 20 Shareholders QoQ Holding Ratio Change (%)**: Quarter-over-quarter change in Top 20 Holding.

# Sheet 2: "Key Shareholders Details"

* **Rows**: One row per Top 20 institution per quarter.
* **Columns**:

  1. **Quarter**: Quarter of record.
  2. **Shareholder Name**: Institution name.
  3. **Shares Held (Million Shares)**: Number of shares held.
  4. **Holding Value (Billion USD)**: Value of holdings in billions USD.
  5. **Holding Ratio (%)**: Institution's holding percentage vs. total outstanding shares.
  6. **Change from Last Quarter (Million Shares)**: Change in shares from prior quarter, in millions.
  7. **Change Type (New/Increase/Decrease/Exit)**: One of {New, Increase, Decrease, Exit}.

# Sheet 3: "Position Adjustment Summary"

* **Rows**: Each row represents one quarter from 2023 Q1 through 2024 Q4.
* **Columns**:

  1. **Quarter**: Label of the quarter.
  2. **New Entry Shareholders Count**: Count of institutions new.
  3. **Increase Shareholders Count**: Count of institutions that increased holdings.
  4. **Decrease Shareholders Count**: Count of institutions that decreased holdings.
  5. **Exit Shareholders Count**: Count of institutions that exited.
  6. **Net Increase Shareholders (Increase - Decrease)**: Increases minus Decreases.
  7. **Large Adjustment Count (Over 10M Shares)**: Number of institutions with |change| > 10M shares.
  8. **Quarterly Net Fund Inflow (Billion USD)**: Net share change × stock price.

# Sheet 4: "Conclusions & Trends"

* **Rows**: Each row is an indicator.
* **Columns**:

  1. **Indicator**: Descriptive name.
  2. **Value**: A string representation of a Python list.

Indicators include:

* **Top 5 Most Active Adjustment Institutions**
* **List of Large Institutions with Continuous Increase**
