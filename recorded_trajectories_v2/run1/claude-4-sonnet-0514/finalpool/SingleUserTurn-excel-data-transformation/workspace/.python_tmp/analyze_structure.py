import pandas as pd
import numpy as np

# Read the Excel file
df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

# Let's analyze the structure more systematically
print("Understanding the data structure:")
print("="*50)

# The first row contains sub-headers
print("Sub-headers from first row:")
print(df.iloc[0, 1:13].values)

print("\n" + "="*50)
print("Main column headers:")
main_headers = [
    'Sales Volume of Household Refrigerators',
    'Production Volume of Air Conditioners', 
    'Production Volume of Household Washing Machines'
]

for i, header in enumerate(main_headers):
    col_idx = 1 + i * 4  # Each product has 4 metrics
    print(f"{header}: columns {col_idx} to {col_idx + 3}")

print("\n" + "="*50)
print("Summary section:")
print("Time column:", df.columns[14])
print("Product columns:", df.columns[15:18])

# Let's look at the summary section data
print("\nSummary section data (first 10 rows):")
summary_data = df.iloc[:10, [14, 15, 16, 17]]
print(summary_data)