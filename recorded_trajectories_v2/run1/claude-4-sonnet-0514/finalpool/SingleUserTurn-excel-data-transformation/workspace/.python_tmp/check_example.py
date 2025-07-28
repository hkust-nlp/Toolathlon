import pandas as pd

# Check the Format_Example file first
example_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx"

try:
    df_example = pd.read_excel(example_path)
    print("Example file shape:", df_example.shape)
    print("Example columns:", df_example.columns.tolist())
    print("Example data:")
    print(df_example.head())
except Exception as e:
    print(f"Error reading example file: {e}")