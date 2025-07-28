import pandas as pd

# Read the original data and examine its structure more carefully
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Let's try to read with different parameters to better understand the structure
df_raw = pd.read_excel(file_path, header=None)
print("Raw data (first 10 rows, first 10 columns):")
print(df_raw.iloc[:10, :10])
print("\n" + "="*50 + "\n")

# Let's also try reading with header=0
df_header = pd.read_excel(file_path, header=0)
print("Data with header=0 (first 5 rows):")
print(df_header.head())
print("\nColumns:", df_header.columns.tolist())