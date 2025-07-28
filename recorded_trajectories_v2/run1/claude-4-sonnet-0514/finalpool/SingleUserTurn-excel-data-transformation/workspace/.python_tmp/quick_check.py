import pandas as pd

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read with header=0 (default)
df = pd.read_excel(file_path)
print("Shape:", df.shape)
print("Columns:", list(df.columns))
print("\nSample data:")
print(df.iloc[:3, :6])  # First 3 rows, first 6 columns