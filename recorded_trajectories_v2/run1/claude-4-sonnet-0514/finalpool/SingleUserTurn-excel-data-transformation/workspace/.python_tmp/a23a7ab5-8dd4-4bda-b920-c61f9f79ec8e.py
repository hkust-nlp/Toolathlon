import pandas as pd
import numpy as np

# Read the original data and transform it
df_raw = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

# Extract the data starting from row 2 (skip the header rows)
data_rows = df_raw.iloc[2:].copy()
time_data = data_rows.iloc[:, 0]

# Create lists to store the transformed data
transformed_data = []

# Define appliance types and their column ranges
appliances = {
    'Household Refrigerator': (1, 5),  # columns 1-4
    'Air Conditioner': (5, 9),        # columns 5-8  
    'Household Washing Machines': (9, 13)  # columns 9-12
}

# Process each time period
for idx, time_val in enumerate(time_data):
    if pd.isna(time_val):
        continue
        
    # For each appliance type
    for appliance_name, (start_col, end_col) in appliances.items():
        # Extract the data for this appliance
        appliance_data = data_rows.iloc[idx, start_col:end_col]
        
        # Create a row for this appliance at this time
        row = {
            'Time': time_val,
            'Appliance types': appliance_name,
            'Current Period Sales(Ten Thousand Units)': appliance_data.iloc[0] if len(appliance_data) > 0 else np.nan,
            'Accumulated Sales (Ten Thousand Units)': appliance_data.iloc[1] if len(appliance_data) > 1 else np.nan,
            'Year-on-Year Growth (%)': appliance_data.iloc[2] if len(appliance_data) > 2 else np.nan,
            'Accumulated Growth (%)': appliance_data.iloc[3] if len(appliance_data) > 3 else np.nan
        }
        
        transformed_data.append(row)

# Create the final DataFrame
result_df = pd.DataFrame(transformed_data)

# Let's examine the data more carefully
print("Sample of transformed data:")
print(result_df.head(15).to_string())

# Check the unique appliance types
print(f"\nUnique appliance types:")
print(result_df['Appliance types'].unique())

# Check some statistics
print(f"\nNon-null counts by column:")
print(result_df.count())

# Let's also check a few specific rows from the original data to verify transformation
print(f"\nOriginal data row 2 (first data row):")
print(df_raw.iloc[2, :13].tolist())

print(f"\nCorresponding transformed rows (first 3 rows for 2025-03-01):")
march_2025_data = result_df[result_df['Time'] == '2025-03-01']
print(march_2025_data.to_string())