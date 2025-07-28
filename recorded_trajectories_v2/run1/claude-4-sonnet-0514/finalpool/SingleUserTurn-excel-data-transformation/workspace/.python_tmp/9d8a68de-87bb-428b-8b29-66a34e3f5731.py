import pandas as pd
import numpy as np

# Read format example
format_example = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')

# Let's see the full format example
print("Full format example:")
print(format_example.to_string())

# Check unique appliance types
print("\nUnique appliance types:")
print(format_example['Appliance types'].unique())