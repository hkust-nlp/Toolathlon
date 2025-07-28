import pandas as pd
import numpy as np

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read the data
df = pd.read_excel(file_path)

# Remove the first row (sub-headers) and reset index
df_data = df.iloc[1:].reset_index(drop=True)

# Extract time column
time_col = df_data.iloc[:, 0]

# Define the column groups for each appliance
appliances = {
    'Household Refrigerator': {
        'current_sales': 1,
        'accumulated_sales': 2, 
        'year_growth': 3,
        'accumulated_growth': 4
    },
    'Air Conditioner': {
        'current_sales': 5,
        'accumulated_sales': 6,
        'year_growth': 7, 
        'accumulated_growth': 8
    },
    'Household Washing Machines': {
        'current_sales': 9,
        'accumulated_sales': 10,
        'year_growth': 11,
        'accumulated_growth': 12
    }
}

# Create the transformed data
transformed_data = []

for idx, time_val in enumerate(time_col):
    if pd.isna(time_val):
        continue
        
    for appliance_name, cols in appliances.items():
        row = {
            'Time': time_val,
            'Appliance types': appliance_name,
            'Current Period Sales(Ten Thousand Units)': df_data.iloc[idx, cols['current_sales']],
            'Accumulated Sales (Ten Thousand Units)': df_data.iloc[idx, cols['accumulated_sales']],
            'Year-on-Year Growth (%)': df_data.iloc[idx, cols['year_growth']],
            'Accumulated Growth (%)': df_data.iloc[idx, cols['accumulated_growth']]
        }
        transformed_data.append(row)

# Create DataFrame
result_df = pd.DataFrame(transformed_data)

print("Transformed data shape:", result_df.shape)
print("Sample transformed data:")
print(result_df.head(10))