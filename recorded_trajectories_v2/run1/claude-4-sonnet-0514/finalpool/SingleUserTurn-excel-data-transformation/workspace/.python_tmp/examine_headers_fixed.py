import pandas as pd
import numpy as np

# Read the current data with header=None to see the raw structure
df_raw = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

print("First few rows with all columns:")
for i in range(3):
    print(f"Row {i}:")
    for j in range(18):
        print(f"  Col {j}: {df_raw.iloc[i, j]}")
    print()