import pandas as pd

# Try reading the original file with different parameters
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read just the first few rows to understand structure
df = pd.read_excel(file_path, nrows=10)
print("Shape:", df.shape)
print("Columns:")
for i, col in enumerate(df.columns):
    print(f"{i}: '{col}'")
    
print("\nFirst few rows:")
for i in range(min(5, len(df))):
    print(f"Row {i}:", df.iloc[i].tolist()[:8])  # First 8 values only