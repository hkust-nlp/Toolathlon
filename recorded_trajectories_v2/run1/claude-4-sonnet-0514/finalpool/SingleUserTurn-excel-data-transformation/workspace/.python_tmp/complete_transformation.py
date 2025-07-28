import pandas as pd
import numpy as np

# Recreate the transformation and save (since variables were lost)
file_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx'
df_raw = pd.read_excel(file_path, header=None)

# Extract the time column
time_data = df_raw.iloc[2:, 0].reset_index(drop=True)

# Define the column structure based on the headers we observed
columns_mapping = {
    'Household Refrigerators': {
        'Current Period Sales(Ten Thousand Units)': 1,
        'Accumulated Sales (Ten Thousand Units)': 2,
        'Year-on-Year Growth (%)': 3,
        'Accumulated Growth (%)': 4
    },
    'Air Conditioners': {
        'Current Period Sales(Ten Thousand Units)': 5,
        'Accumulated Sales (Ten Thousand Units)': 6,
        'Year-on-Year Growth (%)': 7,
        'Accumulated Growth (%)': 8
    },
    'Household Washing Machines': {
        'Current Period Sales(Ten Thousand Units)': 9,
        'Accumulated Sales (Ten Thousand Units)': 10,
        'Year-on-Year Growth (%)': 11,
        'Accumulated Growth (%)': 12
    }
}

# Also include the additional accumulated growth data from columns 15-17
additional_growth = {
    'Household Refrigerators': 15,
    'Air Conditioners': 16,
    'Household Washing Machines': 17
}

# Create the one-dimensional format
transformed_data = []

# Process main data (columns 1-12)
for appliance, metrics in columns_mapping.items():
    for metric_name, col_idx in metrics.items():
        data_series = df_raw.iloc[2:, col_idx].reset_index(drop=True)
        
        for i, (time_val, value) in enumerate(zip(time_data, data_series)):
            if pd.notna(value) and pd.notna(time_val):
                transformed_data.append({
                    'Time': time_val,
                    'Appliance_Type': appliance,
                    'Metric': metric_name,
                    'Value': value
                })

# Process additional accumulated growth data (columns 15-17)
for appliance, col_idx in additional_growth.items():
    data_series = df_raw.iloc[2:, col_idx].reset_index(drop=True)
    # Use the time data from column 14 for this section
    time_series_alt = df_raw.iloc[2:, 14].reset_index(drop=True)
    
    for i, (time_val, value) in enumerate(zip(time_series_alt, data_series)):
        if pd.notna(value) and pd.notna(time_val):
            transformed_data.append({
                'Time': time_val,
                'Appliance_Type': appliance,
                'Metric': 'Additional Accumulated Growth (%)',
                'Value': value
            })

# Create DataFrame from transformed data
df_transformed = pd.DataFrame(transformed_data)

# Sort by time and appliance type for better organization
df_transformed = df_transformed.sort_values(['Time', 'Appliance_Type', 'Metric']).reset_index(drop=True)

# Save the transformed data to Excel
output_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'

# Convert datetime to a more readable format
df_transformed['Time'] = pd.to_datetime(df_transformed['Time']).dt.strftime('%Y-%m-%d')

# Save to Excel
df_transformed.to_excel(output_path, index=False)

print(f"Processed data saved to: {output_path}")
print("\nFinal data summary:")
print(f"Total records: {len(df_transformed)}")
print(f"Date range: {df_transformed['Time'].min()} to {df_transformed['Time'].max()}")
print(f"Appliance types: {len(df_transformed['Appliance_Type'].unique())}")
print(f"Metrics per appliance: {len(df_transformed['Metric'].unique())}")

# Show a sample of the final data
print("\nSample of final transformed data:")
print(df_transformed.head(15))