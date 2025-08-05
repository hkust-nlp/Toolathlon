import pandas as pd
import numpy as np
from datetime import datetime

# Read the raw data
df_raw = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

# Initialize the output list
output_data = []

# Define appliance types
appliance_types = ['Household Refrigerator', 'Air Conditioner', 'Household Washing Machines']

# Process each row starting from row 2 (where actual data begins)
for i in range(2, len(df_raw)):
    time_value = df_raw.iloc[i, 0]
    
    # Skip rows with no time data
    if pd.isna(time_value):
        continue
    
    # Format time as YYYY-MM
    if isinstance(time_value, datetime):
        time_str = time_value.strftime('%Y-%m')
    else:
        time_str = str(time_value)[:7]  # Take first 7 characters (YYYY-MM)
    
    # Extract data for each appliance type
    # Household Refrigerators: columns 1-4
    ref_data = df_raw.iloc[i, 1:5].values
    if not all(pd.isna(ref_data)):
        output_data.append({
            'Time': time_str,
            'Appliance types': appliance_types[0],
            'Current Period Sales(Ten Thousand Units)': ref_data[0] if not pd.isna(ref_data[0]) else None,
            'Accumulated Sales (Ten Thousand Units)': ref_data[1] if not pd.isna(ref_data[1]) else None,
            'Year-on-Year Growth (%)': ref_data[2] if not pd.isna(ref_data[2]) else None,
            'Accumulated Growth (%)': ref_data[3] if not pd.isna(ref_data[3]) else None
        })
    
    # Air Conditioners: columns 5-8
    ac_data = df_raw.iloc[i, 5:9].values
    if not all(pd.isna(ac_data)):
        output_data.append({
            'Time': time_str,
            'Appliance types': appliance_types[1],
            'Current Period Sales(Ten Thousand Units)': ac_data[0] if not pd.isna(ac_data[0]) else None,
            'Accumulated Sales (Ten Thousand Units)': ac_data[1] if not pd.isna(ac_data[1]) else None,
            'Year-on-Year Growth (%)': ac_data[2] if not pd.isna(ac_data[2]) else None,
            'Accumulated Growth (%)': ac_data[3] if not pd.isna(ac_data[3]) else None
        })
    
    # Household Washing Machines: columns 9-12
    wm_data = df_raw.iloc[i, 9:13].values
    if not all(pd.isna(wm_data)):
        output_data.append({
            'Time': time_str,
            'Appliance types': appliance_types[2],
            'Current Period Sales(Ten Thousand Units)': wm_data[0] if not pd.isna(wm_data[0]) else None,
            'Accumulated Sales (Ten Thousand Units)': wm_data[1] if not pd.isna(wm_data[1]) else None,
            'Year-on-Year Growth (%)': wm_data[2] if not pd.isna(wm_data[2]) else None,
            'Accumulated Growth (%)': wm_data[3] if not pd.isna(wm_data[3]) else None
        })

# Create DataFrame from the output data
df_processed = pd.DataFrame(output_data)

print(f"Processed data shape: {df_processed.shape}")
print("\nFirst 10 rows of processed data:")
print(df_processed.head(10))
print("\nUnique appliance types:")
print(df_processed['Appliance types'].unique())
print("\nData types:")
print(df_processed.dtypes)