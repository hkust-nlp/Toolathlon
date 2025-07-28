import pandas as pd

# Read the original data and examine its structure more carefully
df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

print("Column names:")
for i, col in enumerate(df.columns):
    print(f"{i}: {col}")
    
print(f"\nFirst few rows with all columns:")
# Display first few rows with better formatting
for i in range(5):
    print(f"\nRow {i}:")
    for j, col in enumerate(df.columns):
        print(f"  {j} ({col}): {df.iloc[i, j]}")