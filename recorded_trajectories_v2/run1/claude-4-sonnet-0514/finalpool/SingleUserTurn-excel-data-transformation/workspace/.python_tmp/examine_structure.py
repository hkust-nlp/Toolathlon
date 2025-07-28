import pandas as pd

# Read the Excel file with header=None to see the raw structure
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read without header to see the raw structure
df_raw = pd.read_excel(file_path, header=None)
print("Raw data shape:", df_raw.shape)
print("\nFirst few rows (raw):")
print(df_raw.head(10))

# Let's also check the first few rows with default header
df = pd.read_excel(file_path)
print("\n\nWith default header:")
print("Column names:")
for i, col in enumerate(df.columns):
    print(f"{i}: {col}")
    
print("\nFirst 5 rows:")
print(df.head())