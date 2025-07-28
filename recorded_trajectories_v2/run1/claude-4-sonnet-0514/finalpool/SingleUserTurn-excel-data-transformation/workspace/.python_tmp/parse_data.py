import pandas as pd
import numpy as np

file_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx'

# Read the data with proper header handling
df_raw = pd.read_excel(file_path, header=None)

# Extract the time column (column 0, starting from row 2)
time_data = df_raw.iloc[2:, 0].reset_index(drop=True)

# Define the structure based on what we observed
appliance_data = {
    'Household Refrigerators': {
        'Current Period Sales(Ten Thousand Units)': df_raw.iloc[2:, 1].reset_index(drop=True),
        'Accumulated Sales (Ten Thousand Units)': df_raw.iloc[2:, 2].reset_index(drop=True),
        'Year-on-Year Growth (%)': df_raw.iloc[2:, 3].reset_index(drop=True),
        'Accumulated Growth (%)': df_raw.iloc[2:, 4].reset_index(drop=True)
    },
    'Air Conditioners': {
        'Current Period Sales(Ten Thousand Units)': df_raw.iloc[2:, 5].reset_index(drop=True),
        'Accumulated Sales (Ten Thousand Units)': df_raw.iloc[2:, 6].reset_index(drop=True),
        'Year-on-Year Growth (%)': df_raw.iloc[2:, 7].reset_index(drop=True),
        'Accumulated Growth (%)': df_raw.iloc[2:, 8].reset_index(drop=True)
    },
    'Household Washing Machines': {
        'Current Period Sales(Ten Thousand Units)': df_raw.iloc[2:, 9].reset_index(drop=True),
        'Accumulated Sales (Ten Thousand Units)': df_raw.iloc[2:, 10].reset_index(drop=True),
        'Year-on-Year Growth (%)': df_raw.iloc[2:, 11].reset_index(drop=True),
        'Accumulated Growth (%)': df_raw.iloc[2:, 12].reset_index(drop=True)
    }
}

# Also get the accumulated growth data from columns 15-17
accumulated_growth_data = {
    'Household Refrigerators': df_raw.iloc[2:, 15].reset_index(drop=True),
    'Air Conditioners': df_raw.iloc[2:, 16].reset_index(drop=True),
    'Household Washing Machines': df_raw.iloc[2:, 17].reset_index(drop=True)
}

print("Time data shape:", time_data.shape)
print("Sample time data:")
print(time_data.head())
print("\nSample appliance data for Household Refrigerators:")
for metric, data in appliance_data['Household Refrigerators'].items():
    print(f"{metric}: {data.head(3).tolist()}")
    
print("\nSample accumulated growth data:")
for appliance, data in accumulated_growth_data.items():
    print(f"{appliance}: {data.head(3).tolist()}")