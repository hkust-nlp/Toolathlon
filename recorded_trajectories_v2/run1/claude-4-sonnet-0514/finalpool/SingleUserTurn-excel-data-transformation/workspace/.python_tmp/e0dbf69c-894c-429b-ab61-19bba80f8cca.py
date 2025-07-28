import pandas as pd

# Read the format example
try:
    df_example = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')
    print("Format example:")
    print(df_example.head(10))
    print(f"\nShape: {df_example.shape}")
    print(f"\nColumns: {df_example.columns.tolist()}")
except Exception as e:
    print(f"Error reading format example: {e}")