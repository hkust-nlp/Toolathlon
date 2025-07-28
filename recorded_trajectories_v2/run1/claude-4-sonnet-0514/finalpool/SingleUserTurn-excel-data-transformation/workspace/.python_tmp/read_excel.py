import pandas as pd
import openpyxl

# Read the Excel file to understand its structure
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# First, let's see what sheets are available
try:
    workbook = openpyxl.load_workbook(file_path)
    sheet_names = workbook.sheetnames
    print("Available sheets:", sheet_names)
    
    # Read the data using pandas
    df = pd.read_excel(file_path)
    print("\nOriginal data shape:", df.shape)
    print("\nColumn names:")
    print(df.columns.tolist())
    print("\nFirst few rows:")
    print(df.head())
    print("\nData types:")
    print(df.dtypes)
    
except Exception as e:
    print(f"Error reading file: {e}")