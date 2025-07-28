import pandas as pd
import numpy as np

# Read the Excel file
file_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx'

try:
    df = pd.read_excel(file_path)
    print("Original data structure:")
    print(df.head(10))
    print("\nColumn names:")
    print(df.columns.tolist())
    print("\nData shape:", df.shape)
    print("\nData types:")
    print(df.dtypes)
except Exception as e:
    print(f"Error reading file: {e}")