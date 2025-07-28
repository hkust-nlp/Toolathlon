import pandas as pd
import numpy as np

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read just first 10 rows to test
df = pd.read_excel(file_path, nrows=10)
df_data = df.iloc[1:].reset_index(drop=True)

print("Sample data for transformation:")
print("Time column:", df_data.iloc[:5, 0].tolist())
print("Refrigerator data:", df_data.iloc[3, 1:5].tolist())
print("Air Conditioner data:", df_data.iloc[3, 5:9].tolist())
print("Washing Machine data:", df_data.iloc[3, 9:13].tolist())