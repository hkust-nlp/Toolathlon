import pandas as pd

# Let's examine the Format_Example.xlsx to understand the desired output format
format_example_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx"
format_df = pd.read_excel(format_example_path)

print("Format Example structure:")
print(format_df.head(10))
print("\nColumn names:")
print(format_df.columns.tolist())
print("\nData shape:", format_df.shape)