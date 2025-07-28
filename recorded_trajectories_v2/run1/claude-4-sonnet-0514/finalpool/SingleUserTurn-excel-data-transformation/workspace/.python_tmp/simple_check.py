import pandas as pd

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read just a small portion to understand the structure
df = pd.read_excel(file_path, nrows=5)

# Check the first row which contains sub-headers
first_row = df.iloc[0]
print("First row values:")
for i, val in enumerate(first_row):
    if pd.notna(val):
        print(f"Column {i}: {val}")

# Get the main column names
print("\nMain column names:")
for i, col in enumerate(df.columns):
    print(f"Column {i}: {col}")
    if i > 15:  # Limit output
        break