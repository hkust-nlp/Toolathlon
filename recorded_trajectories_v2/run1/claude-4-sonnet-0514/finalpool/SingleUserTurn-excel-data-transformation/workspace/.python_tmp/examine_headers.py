import pandas as pd
import numpy as np

file_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx'

df_raw = pd.read_excel(file_path, header=None)

# Let's examine the first few rows to understand the header structure
print("First 3 rows of raw data:")
for i in range(3):
    print(f"Row {i}:")
    row_data = df_raw.iloc[i].tolist()
    for j, val in enumerate(row_data):
        if pd.notna(val):
            print(f"  Column {j}: {val}")
    print()