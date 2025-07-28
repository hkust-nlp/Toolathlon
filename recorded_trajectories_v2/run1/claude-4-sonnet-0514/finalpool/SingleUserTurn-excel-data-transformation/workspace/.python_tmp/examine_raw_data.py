import pandas as pd
import numpy as np

# Let's look at the raw data without headers to understand the structure
file_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx'

df_raw = pd.read_excel(file_path, header=None)
print("Raw data (first 15 rows):")
print(df_raw.head(15))
print("\nRaw data shape:", df_raw.shape)