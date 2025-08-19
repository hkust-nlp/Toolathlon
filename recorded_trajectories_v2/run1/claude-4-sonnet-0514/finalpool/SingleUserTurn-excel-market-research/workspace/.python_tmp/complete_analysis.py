import pandas as pd
import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Read the Market_Data.xlsx file
file_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-market-research/workspace/Market_Data.xlsx'

# Load the methodology sheet
methodology_df = pd.read_excel(file_path, sheet_name='Methodology', header=None)

# Load the raw data sheet
raw_data_df = pd.read_excel(file_path, sheet_name='RawData', header=None)

# Now let's analyze the methodology mapping
print("Methodology mapping analysis:")
print("Row 1 (market categories):", methodology_df.iloc[1, 1:].tolist())
print("Row 2 (data sources):", methodology_df.iloc[2, 1:].tolist())

# Company internal categories and their mappings
print("\nCompany internal categories and their mappings:")
for i in range(3, 13):  # Rows 4-13 contain the mappings
    internal_category = methodology_df.iloc[i, 1]
    if pd.notna(internal_category):
        mappings = methodology_df.iloc[i, 2:].tolist()
        non_null_mappings = [(j+2, val) for j, val in enumerate(mappings) if pd.notna(val) and val != 0]
        print(f"{internal_category}: {non_null_mappings}")

print("\nRaw data market categories (row 3):", raw_data_df.iloc[3, 1:].tolist())