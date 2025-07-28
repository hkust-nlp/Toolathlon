import pandas as pd
import numpy as np

# Read the original data without headers first
df_raw = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx', header=None)

# The data structure based on our analysis:
# Column 0: Time
# Columns 1-4: Household Refrigerators (Current Period, Accumulated, YoY Growth, Accumulated Growth)
# Columns 5-8: Air Conditioners (Current Period, Accumulated, YoY Growth, Accumulated Growth)
# Columns 9-12: Household Washing Machines (Current Period, Accumulated, YoY Growth, Accumulated Growth)

# Extract the data starting from row 2 (skip the header rows)
data_rows = df_raw.iloc[2:].copy()

# Extract time column
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

# Display the first few rows to verify
print("Transformed data (first 10 rows):")
print(result_df.head(10))
print(f"\nTotal rows: {len(result_df)}")
print(f"Shape: {result_df.shape}")

# Check for any issues with the data
print(f"\nData types:")
print(result_df.dtypes)