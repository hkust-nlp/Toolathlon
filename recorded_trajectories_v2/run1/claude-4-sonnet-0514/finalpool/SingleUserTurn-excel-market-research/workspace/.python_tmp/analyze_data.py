import pandas as pd
import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Read the Market_Data.xlsx file
file_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-market-research/workspace/Market_Data.xlsx'

# Load the methodology sheet
methodology_df = pd.read_excel(file_path, sheet_name='Methodology', header=None)
print("Methodology sheet shape:", methodology_df.shape)
print("Methodology sheet:")
print(methodology_df.head(15))