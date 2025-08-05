import pandas as pd
import numpy as np

# Read the current data with header=None to see the raw structure
df_raw = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

print("Raw data structure:")
print("Shape:", df_raw.shape)
print("\nFirst 10 rows:")
print(df_raw.head(10))
print("\nLast 5 rows:")
print(df_raw.tail())