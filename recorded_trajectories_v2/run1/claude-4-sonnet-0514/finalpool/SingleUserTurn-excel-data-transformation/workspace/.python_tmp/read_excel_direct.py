import pandas as pd
import numpy as np

# Read the Excel file
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read all sheets to understand the structure
xl_file = pd.ExcelFile(file_path)
print("Sheet names:", xl_file.sheet_names)

# Read the first sheet
df = pd.read_excel(file_path, sheet_name=0)
print(f"Data shape: {df.shape}")

# Find rows with valid time data
time_mask = df['Time'].notna()
print(f"Rows with valid time data: {time_mask.sum()}")

# Get the clean data
df_clean = df[time_mask].copy()
print("Sample of clean data:")
print(df_clean.iloc[0:3, 0:6])  # First 3 rows, first 6 columns