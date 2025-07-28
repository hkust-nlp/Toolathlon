import pandas as pd

# Try reading the Excel file with basic settings
try:
    df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')
    print("Successfully loaded the file")
    print(f"Shape: {df.shape}")
    print("\nFirst 5 rows:")
    print(df.head())
except Exception as e:
    print(f"Error reading file: {e}")