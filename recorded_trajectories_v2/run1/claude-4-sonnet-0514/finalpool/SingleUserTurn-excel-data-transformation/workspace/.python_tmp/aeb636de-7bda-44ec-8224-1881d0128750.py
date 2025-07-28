import pandas as pd
import numpy as np

# Read the original data without assuming headers
df_original = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

print("Original data structure (without header assumption):")
print(df_original.head(10))
print(f"\nShape: {df_original.shape}")

# Also try reading with different header options
df_with_header = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')
print("\n" + "="*50)
print("Data with default header reading:")
print(df_with_header.head(10))