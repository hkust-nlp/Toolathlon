import pandas as pd
import numpy as np

file_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx'
df_raw = pd.read_excel(file_path, header=None)

# Let's examine all columns to see which ones have actual data
print("Examining data availability in each column:")
for col in range(18):
    col_data = df_raw.iloc[2:, col]
    non_null_count = col_data.notna().sum()
    if non_null_count > 0:
        print(f"Column {col}: {non_null_count} non-null values")
        print(f"  Sample values: {col_data.dropna().head(3).tolist()}")
        print()

# Let's also check if there might be string values that look like numbers
print("\nChecking for string numeric values:")
for col in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
    col_data = df_raw.iloc[2:, col]
    sample_values = col_data.dropna().head(5).tolist()
    if sample_values:
        print(f"Column {col} sample values: {sample_values}")