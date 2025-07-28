import pandas as pd
import numpy as np

# Read the Excel file
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"
df = pd.read_excel(file_path)

# Get clean data (rows with valid time)
df_clean = df[df['Time'].notna()].copy()

# Let's examine the column names and identify the pattern
print("All column names:")
for i, col in enumerate(df.columns):
    print(f"{i}: {col}")

print(f"\nClean data shape: {df_clean.shape}")

# Look at a few rows with actual data (not NaN)
print("\nLooking for rows with actual data:")
for i in range(len(df_clean)):
    row = df_clean.iloc[i]
    non_null_count = row.notna().sum()
    if non_null_count > 2:  # More than just Time column
        print(f"Row {i} (Time: {row['Time']}): {non_null_count} non-null values")
        print("Non-null columns:", [col for col in df_clean.columns if pd.notna(row[col])])
        break