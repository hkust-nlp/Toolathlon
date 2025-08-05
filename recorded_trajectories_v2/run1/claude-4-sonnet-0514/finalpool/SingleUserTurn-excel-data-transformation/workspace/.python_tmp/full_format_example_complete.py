import pandas as pd
import numpy as np

# Read the format example
df_example = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')

print("Full format example:")
print(df_example)
print("\nUnique appliance types:")
print(df_example['Appliance types'].unique())