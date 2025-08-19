import pandas as pd
import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Read the Market_Data.xlsx file
file_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-market-research/workspace/Market_Data.xlsx'

# Load the raw data sheet
raw_data_df = pd.read_excel(file_path, sheet_name='RawData', header=None)
print("Raw data sheet shape:", raw_data_df.shape)
print("Raw data sheet headers:")
print(raw_data_df.iloc[0:5])  # First few rows to understand structure