import pandas as pd
import numpy as np

# Read the current household appliances data
df_original = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

print("Original data structure:")
print(df_original.head())
print("\nShape:", df_original.shape)
print("\nColumn names:")
print(df_original.columns.tolist())