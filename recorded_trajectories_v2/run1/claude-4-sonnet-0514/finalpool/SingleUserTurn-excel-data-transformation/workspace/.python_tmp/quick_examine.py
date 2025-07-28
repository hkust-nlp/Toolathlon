import pandas as pd

# Read the original data
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"
df = pd.read_excel(file_path)

# Display the first few rows to understand the structure
print("First 5 rows of the data:")
for i in range(min(5, len(df))):
    print(f"Row {i}:", df.iloc[i].tolist()[:8])  # Show first 8 columns only

print(f"\nTotal columns: {len(df.columns)}")
print(f"Total rows: {len(df)}")