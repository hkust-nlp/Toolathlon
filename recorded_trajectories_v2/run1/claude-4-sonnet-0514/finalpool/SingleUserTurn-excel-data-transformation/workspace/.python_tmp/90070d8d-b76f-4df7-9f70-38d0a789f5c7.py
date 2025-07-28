import pandas as pd
import numpy as np

# Let's check the format example to understand the expected output
format_example = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')

print("Format example structure:")
print("Shape:", format_example.shape)
print("\nColumn names:")
print(format_example.columns.tolist())
print("\nFirst few rows:")
print(format_example.head(10))
print("\nLast few rows:")
print(format_example.tail(5))