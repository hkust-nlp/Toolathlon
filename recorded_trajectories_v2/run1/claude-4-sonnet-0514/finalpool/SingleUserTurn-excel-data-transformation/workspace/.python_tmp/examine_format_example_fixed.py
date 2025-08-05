import pandas as pd
import numpy as np

# Read the format example
df_example = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')

print("Format example structure:")
print("Shape:", df_example.shape)
print("\nColumn names:")
print(df_example.columns.tolist())
print("\nFirst few rows:")
print(df_example.head(10))
print("\nData types:")
print(df_example.dtypes)