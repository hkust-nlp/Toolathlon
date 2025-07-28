import pandas as pd
import os

# Read the Household_Appliances.xlsx file
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"
df = pd.read_excel(file_path)

print("Original data structure:")
print(df.head())
print("\nColumn names:")
print(df.columns.tolist())
print("\nData shape:", df.shape)
print("\nData types:")
print(df.dtypes)