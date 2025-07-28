import pandas as pd
import numpy as np

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read the data
df = pd.read_excel(file_path)

# Get the sub-headers from the first row
sub_headers = df.iloc[0].fillna('').tolist()
main_headers = df.columns.tolist()

print("Main headers:", main_headers[:10])
print("Sub headers:", sub_headers[:10])

# Create a mapping of column positions to appliance types and metrics
column_info = []
for i, (main, sub) in enumerate(zip(main_headers, sub_headers)):
    column_info.append({
        'index': i,
        'main_header': main,
        'sub_header': sub
    })

for info in column_info[:10]:
    print(info)