import pandas as pd

# Read the example file to understand the target format
example_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx"

df_example = pd.read_excel(example_path)
print("Example data (full):")
print(df_example)
print("\nUnique appliance types:")
print(df_example['Appliance types'].unique())