import pandas as pd
import numpy as np

# Read the current household appliances data
df_current = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

print("Current data structure:")
print("Shape:", df_current.shape)
print("\nColumn names:")
print(df_current.columns.tolist())
print("\nFirst few rows:")
print(df_current.head())
print("\nData types:")
print(df_current.dtypes)