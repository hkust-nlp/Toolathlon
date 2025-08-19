import pandas as pd
import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Read the Market_Data.xlsx file
file_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-market-research/workspace/Market_Data.xlsx'

# Load the raw data sheet
raw_data_df = pd.read_excel(file_path, sheet_name='RawData', header=None)

# Now let's extract the data and calculate the Appliance category values
print("Processing Appliance category conversion...")

# Get the years from raw data (starting from row 4, column 0)
years = []
appliance_values = []
electric_percentages = []
construction_percentages = []
furniture_percentages = []

# Extract years and calculate appliance values for each year
for row_idx in range(4, len(raw_data_df)):
    year = raw_data_df.iloc[row_idx, 0]
    if pd.notna(year) and isinstance(year, (int, float)):
        years.append(int(year))
        
        # Calculate appliance value based on methodology:
        # Appliance: [(7, 0.5), (10, 0.2), (11, 0.3)]
        # This means: Electric * 0.5 + Furniture * 0.2 + Construction * 0.3
        
        electric_value = raw_data_df.iloc[row_idx, 7]  # Column 7 is Electric (index 6+1)
        furniture_value = raw_data_df.iloc[row_idx, 10]  # Column 10 is Furniture (index 9+1)
        construction_value = raw_data_df.iloc[row_idx, 11]  # Column 11 is Construction (index 10+1)
        
        # Handle missing values
        electric_value = 0 if pd.isna(electric_value) else electric_value
        furniture_value = 0 if pd.isna(furniture_value) else furniture_value
        construction_value = 0 if pd.isna(construction_value) else construction_value
        
        appliance_value = (electric_value * 0.5 + 
                          furniture_value * 0.2 + 
                          construction_value * 0.3)
        
        appliance_values.append(appliance_value)
        
        # Calculate percentages for the format file
        if appliance_value > 0:
            electric_pct = (electric_value * 0.5) / appliance_value * 100
            furniture_pct = (furniture_value * 0.2) / appliance_value * 100
            construction_pct = (construction_value * 0.3) / appliance_value * 100
        else:
            electric_pct = furniture_pct = construction_pct = 0
            
        electric_percentages.append(electric_pct)
        furniture_percentages.append(furniture_pct)
        construction_percentages.append(construction_pct)
        
        print(f"Year {year}: Electric={electric_value}, Furniture={furniture_value}, Construction={construction_value}, Appliance={appliance_value}")

print(f"\nYears: {years}")
print(f"Appliance values: {appliance_values}")