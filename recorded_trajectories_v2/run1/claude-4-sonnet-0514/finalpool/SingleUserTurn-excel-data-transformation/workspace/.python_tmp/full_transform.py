import pandas as pd
import numpy as np

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read the full data
df = pd.read_excel(file_path)

# Remove the first row (sub-headers) and reset index
df_data = df.iloc[1:].reset_index(drop=True)

# Create empty list for transformed data
transformed_rows = []

# Process each row
for idx in range(len(df_data)):
    time_val = df_data.iloc[idx, 0]
    
    # Skip rows with invalid time
    if pd.isna(time_val):
        continue
    
    # Extract data for each appliance type
    appliances_data = [
        {
            'name': 'Household Refrigerator',
            'current_sales': df_data.iloc[idx, 1],
            'accumulated_sales': df_data.iloc[idx, 2],
            'year_growth': df_data.iloc[idx, 3],
            'accumulated_growth': df_data.iloc[idx, 4]
        },
        {
            'name': 'Air Conditioner', 
            'current_sales': df_data.iloc[idx, 5],
            'accumulated_sales': df_data.iloc[idx, 6],
            'year_growth': df_data.iloc[idx, 7],
            'accumulated_growth': df_data.iloc[idx, 8]
        },
        {
            'name': 'Household Washing Machines',
            'current_sales': df_data.iloc[idx, 9],
            'accumulated_sales': df_data.iloc[idx, 10],
            'year_growth': df_data.iloc[idx, 11],
            'accumulated_growth': df_data.iloc[idx, 12]
        }
    ]
    
    # Create a row for each appliance
    for appliance in appliances_data:
        row = {
            'Time': time_val.strftime('%Y-%m') if hasattr(time_val, 'strftime') else str(time_val),
            'Appliance types': appliance['name'],
            'Current Period Sales(Ten Thousand Units)': appliance['current_sales'],
            'Accumulated Sales (Ten Thousand Units)': appliance['accumulated_sales'],
            'Year-on-Year Growth (%)': appliance['year_growth'],
            'Accumulated Growth (%)': appliance['accumulated_growth']
        }
        transformed_rows.append(row)

# Create the result DataFrame
result_df = pd.DataFrame(transformed_rows)

print(f"Transformation complete!")
print(f"Original shape: {df.shape}")
print(f"Transformed shape: {result_df.shape}")
print(f"\nFirst 10 rows of transformed data:")
print(result_df.head(10))