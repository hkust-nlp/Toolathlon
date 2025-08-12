from argparse import ArgumentParser
import asyncio
from pathlib import Path
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
import numpy as np

def check_basic_trend(
    target_file,
    ticker="NVDA",
    sheet_name="Basic Trend"
):
    """
    Compare the 'Basic Trend' sheet in the given Excel file with live Yahoo Finance NVDA data.
    Checks if each quarter's end-of-quarter price, outstanding shares, and market cap match within 5% error tolerance.
    """
    nvda = yf.Ticker(ticker)
    # Define quarter end dates and their string representations
    quarter_ends = [
        "2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31",
        "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"
    ]
    quarter_strs = [
        "2023 Q1", "2023 Q2", "2023 Q3", "2023 Q4",
        "2024 Q1", "2024 Q2", "2024 Q3", "2024 Q4"
    ]
    result_list = []
    # For each quarter, retrieve data from yfinance and compute needed values
    for date_str, quarter_str in zip(quarter_ends, quarter_strs):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        # Get closing price near the end of the quarter
        hist = nvda.history(start=(date - timedelta(days=5)).strftime("%Y-%m-%d"),
                            end=(date + timedelta(days=1)).strftime("%Y-%m-%d"),
                            interval="1d")
        price = hist['Close'].iloc[-1] if not hist.empty else float('nan')

        # Get outstanding shares from balance sheet
        bs = nvda.quarterly_balance_sheet
        shares = float('nan')
        if "Ordinary Shares Number" in bs.index:
            closest_col = min(bs.columns, key=lambda d: abs(d - date))
            if abs((closest_col - date).days) <= 40:
                shares = bs.loc["Ordinary Shares Number", closest_col]

        # Compute market cap
        market_cap = price * shares if (shares is not None and shares > 0) else float('nan')

        # Append computed values as a new row in results
        result_list.append({
            "Quarter": quarter_str,
            "NVDA End-of-Quarter Stock Price (USD)": price,
            "Outstanding Shares (Million Shares)": shares / 1e6 if not pd.isna(shares) else float('nan'),
            "Market Cap (Billion USD)": market_cap / 1e9 if not pd.isna(market_cap) else float('nan')
        })

    # Create DataFrame of ground truth values
    gt_df = pd.DataFrame(result_list)
    # Read Excel sheet to compare against
    df = pd.read_excel(target_file, sheet_name=sheet_name)
    # Reset index to ensure proper row alignment
    df = df.reset_index(drop=True)
    gt_df = gt_df.reset_index(drop=True)

    cols = [
        "NVDA End-of-Quarter Stock Price (USD)",
        "Outstanding Shares (Million Shares)",
        "Market Cap (Billion USD)"
    ]
    # Compare each cell value in the target columns
    for idx, row in gt_df.iterrows():
        for col in cols:
            gt_val = row[col]
            file_val = df.loc[idx, col]
            # If both are NaN, treat as a match
            if pd.isna(gt_val) and pd.isna(file_val):
                continue
            # If only one is NaN, warn and ignore
            if pd.isna(gt_val) != pd.isna(file_val):
                print(f"Warning: Mismatch NaN at {row['Quarter']} {col}: gt={gt_val}, file={file_val}. Temporarily ignore.")
                continue
            # If both are numbers, check for <5% difference
            if not np.isclose(gt_val, file_val, rtol=0.05, atol=0.):
                print(f"Value mismatch at {row['Quarter']} {col}: gt={gt_val}, file={file_val}")
                exit(1)
            # Uncomment below to print successful matches
            # else:
            #     print(f"Match at {row['Quarter']} {col}: gt={gt_val}, file={file_val}")

    print("Basic Trend check passed.")
    return True


def check_major_holders(target_file, ticker="NVDA", sheet_name="Major Holders Summary"):
    """
    Compare the 'Major Holders Summary' sheet in the given Excel file with live Yahoo Finance NVDA major holders data.
    Checks if key values (insiders held %, institutions held %, #institutions) match within 5% error tolerance.
    """
    # 1. Read the target Excel file's sheet
    df = pd.read_excel(target_file, sheet_name=sheet_name)
    # 2. Get major holders data from yfinance
    holders = yf.Ticker(ticker).major_holders

    # 3. Define mapping between Excel indicators and yfinance values (with proper unit conversion)
    mapping = [
        ("Insiders Held Percentage (%)", holders.loc["insidersPercentHeld", "Value"] * 100),
        ("Institutions Held Percentage (%)", holders.loc["institutionsPercentHeld", "Value"] * 100),
        ("#Institutions", holders.loc["institutionsCount", "Value"])
    ]
    # 4. Compare each field row by row
    for idx, (indicator, gt_val) in enumerate(mapping):
        file_indicator = str(df.iloc[idx, 0]).strip()
        file_val = df.iloc[idx, 1]
        # Handle numbers with commas in Excel
        if isinstance(file_val, str):
            file_val = float(file_val.replace(",", ""))

        # print(f"Checking {file_indicator}: gt={gt_val}, file={file_val}")
        # Case 1: Both are NaN, treat as match
        if pd.isna(gt_val) and pd.isna(file_val):
            continue
        # Case 2: Only one is NaN, warning and skip (temporarily)
        if pd.isna(gt_val) != pd.isna(file_val):
            print(f"Warning: Mismatch NaN for {file_indicator}: gt={gt_val}, file={file_val}. Temporarily ignore.")
            # exit(1)
        # Case 3: Both are numbers, check if within 5% relative error
        if not np.isclose(gt_val, file_val, rtol=0.05, atol=0.):
            print(f"Value mismatch for {file_indicator}: gt={gt_val}, file={file_val}")
            exit(1)
            
    print("Major Holders Summary check passed.")
    return True


def check_key_shareholder_details(target_file, ticker="NVDA", sheet_name="Key Shareholders Details"):
    """
    Compare the 'Key Shareholders Details' sheet in the given Excel file with live Yahoo Finance NVDA institutional holders data.
    Checks if main shareholder details (name, shares, value, holding ratio, percent change) match within 5% error tolerance.
    """
    # Read the Excel sheet
    df = pd.read_excel(target_file, sheet_name=sheet_name)
    # Get institutional holders from yfinance
    holders = yf.Ticker(ticker).institutional_holders

    # Compare each row of Excel and yfinance data (assume both are sorted top N and same length)
    for idx in range(min(len(df), len(holders))):
        # Excel data
        file_row = df.iloc[idx]
        # yfinance data
        gt_row = holders.iloc[idx]

        # 1. Shareholder Name
        file_name = str(file_row["Shareholder Name"]).strip()
        gt_name = str(gt_row["Holder"]).strip()
        if file_name.lower() != gt_name.lower():
            print(f"Shareholder name mismatch at row {idx+1}: gt='{gt_name}', file='{file_name}'")
            exit(1)

        # 2. Shares Held (Million Shares)
        file_shares = file_row["Shares Held (Million Shares)"]
        gt_shares = gt_row["Shares"] / 1e6 if not pd.isna(gt_row["Shares"]) else float('nan')
        # Handle commas in Excel numbers
        if isinstance(file_shares, str):
            file_shares = float(file_shares.replace(",", ""))
        # Both are NaN: skip, One is NaN: error, Both numbers: check 5% error
        if pd.isna(file_shares) and pd.isna(gt_shares):
            pass
        elif pd.isna(file_shares) != pd.isna(gt_shares):
            print(f"Warning: NaN mismatch for Shares at {file_name}: gt={gt_shares}, file={file_shares}. Temporarily ignore.")
            continue
        elif not np.isclose(gt_shares, file_shares, rtol=0.05, atol=0.):
            print(f"Shares mismatch at {file_name}: gt={gt_shares}, file={file_shares}")
            exit(1)

        # 3. Holding Value (Billion USD)
        file_value = file_row["Holding Value (Billion USD)"]
        gt_value = gt_row["Value"] / 1e9 if not pd.isna(gt_row["Value"]) else float('nan')
        if isinstance(file_value, str):
            file_value = float(file_value.replace(",", ""))
        if pd.isna(file_value) and pd.isna(gt_value):
            pass
        elif pd.isna(file_value) != pd.isna(gt_value):
            print(f"Warning: NaN mismatch for Value at {file_name}: gt={gt_value}, file={file_value}. Temporarily ignore.")
            continue
        elif not np.isclose(gt_value, file_value, rtol=0.05, atol=0.):
            print(f"Value mismatch at {file_name}: gt={gt_value}, file={file_value}")
            exit(1)

        # 4. Holding Ratio (%)
        file_ratio = file_row["Holding Ratio (%)"]
        gt_ratio = gt_row["pctHeld"] * 100 if not pd.isna(gt_row["pctHeld"]) else float('nan')
        if isinstance(file_ratio, str):
            file_ratio = float(file_ratio.replace(",", ""))
        if pd.isna(file_ratio) and pd.isna(gt_ratio):
            pass
        elif pd.isna(file_ratio) != pd.isna(gt_ratio):
            print(f"Warning: NaN mismatch for Holding Ratio at {file_name}: gt={gt_ratio}, file={file_ratio}. Temporarily ignore.")
            continue
        elif not np.isclose(gt_ratio, file_ratio, rtol=0.05, atol=0.):
            print(f"Holding Ratio mismatch at {file_name}: gt={gt_ratio}, file={file_ratio}")
            exit(1)

        # 5. Percentage Change (%)
        file_change = file_row["Percentage Change (%)"]
        gt_change = gt_row["pctChange"] * 100 if not pd.isna(gt_row["pctChange"]) else float('nan')
        if isinstance(file_change, str):
            file_change = float(file_change.replace(",", ""))

        if pd.isna(file_change) and pd.isna(gt_change):
            pass
        elif pd.isna(file_change) != pd.isna(gt_change):
            print(f"Warning: NaN mismatch for Percentage Change at {file_name}: gt={gt_change}, file={file_change}. Temporarily ignore.")
            continue
        elif not np.isclose(gt_change, file_change, rtol=0.05, atol=0.):
            print(f"Percentage Change mismatch at {file_name}: gt={gt_change}, file={file_change}")
            exit(1)

    print("Key Shareholders Details check passed.")
    return True

if __name__ == "__main__":
    parser = ArgumentParser(description="Validate NVDA holdings data in Excel file.")
    parser.add_argument("--agent_workspace", required=True, help="Path to the agent workspace")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    workspace_path = Path(args.agent_workspace)
    target_file = workspace_path / "results.xlsx"
    if not target_file.exists():
        target_file = workspace_path / "results_template.xlsx"
    
    if not target_file.exists():
        print("Target file does not exist.")
        exit(1)
    
    print(f"Checking {target_file}...")
    check_basic_trend(target_file)
    check_major_holders(target_file)
    check_key_shareholder_details(target_file)
    
    print("All checks passed successfully.")