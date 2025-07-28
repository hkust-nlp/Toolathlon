import pandas as pd
import numpy as np

# Complete transformation and save
def transform_appliance_data():
    # Read the original data
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
    
    return result_df

# Perform the transformation
result_df = transform_appliance_data()

# Save the transformed data to a new Excel file
output_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'

# Save to Excel
result_df.to_excel(output_path, index=False)

print(f"Successfully saved transformed data to: Processed.xlsx")
print(f"Final dataset shape: {result_df.shape}")
print(f"Columns: {list(result_df.columns)}")

# Show a summary of the final data
print(f"\nFinal data summary:")
print(f"- Total rows: {len(result_df)}")
print(f"- Time periods: {result_df['Time'].nunique()}")
print(f"- Appliance types: {result_df['Appliance types'].nunique()}")
print(f"- Date range: {result_df['Time'].min()} to {result_df['Time'].max()}")

# Show the last few rows to verify
print(f"\nLast 10 rows of the transformed data:")
print(result_df.tail(10).to_string())