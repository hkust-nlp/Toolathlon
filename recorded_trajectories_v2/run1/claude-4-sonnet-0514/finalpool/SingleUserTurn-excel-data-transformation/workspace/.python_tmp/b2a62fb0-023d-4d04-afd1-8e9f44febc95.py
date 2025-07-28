import pandas as pd
import numpy as np

# Read the data
df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

# Let's examine the structure more carefully
print("Looking at the data structure:")
print("The data appears to have multiple sections:")
print("1. Household Refrigerators data in columns 1-4")
print("2. Air Conditioners data in columns 5-8") 
print("3. Household Washing Machines data in columns 9-12")
print("4. Additional data in columns 14-17")

# Extract the main data (skip the header rows that contain metadata)
# Start from row 4 where actual data begins
main_data = df.iloc[4:].copy()

# Extract time column
time_col = main_data.iloc[:, 0].dropna()
print(f"\nTime data shape: {time_col.shape}")
print("First few time values:")
print(time_col.head())

# Extract refrigerator data (columns 1-4)
refrigerator_data = main_data.iloc[:, 1:5].dropna(how='all')
print(f"\nRefrigerator data shape: {refrigerator_data.shape}")
print("Refrigerator data sample:")
print(refrigerator_data.head())