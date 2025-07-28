import pandas as pd
import numpy as np

# Let's examine the raw data without headers to understand the structure better
df_raw = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

print("Raw data structure (first 10 rows, all columns):")
print(df_raw.head(10))
print("\nShape:", df_raw.shape)