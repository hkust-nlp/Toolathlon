import pandas as pd

# Read the data with minimal processing
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read the Excel file
df = pd.read_excel(file_path)

# Process the data row by row manually
result_data = []
columns = ['Time', 'Appliance types', 'Current Period Sales(Ten Thousand Units)', 
          'Accumulated Sales (Ten Thousand Units)', 'Year-on-Year Growth (%)', 'Accumulated Growth (%)']

# Process each row starting from row 1 (skip header row)
for i in range(1, len(df)):
    row = df.iloc[i]
    time_val = row.iloc[0]
    
    # Skip if time is null
    if pd.isna(time_val):
        continue
    
    # Format time
    time_str = time_val.strftime('%Y-%m')
    
    # Create three rows for the three appliances
    result_data.append([time_str, 'Household Refrigerator', row.iloc[1], row.iloc[2], row.iloc[3], row.iloc[4]])
    result_data.append([time_str, 'Air Conditioner', row.iloc[5], row.iloc[6], row.iloc[7], row.iloc[8]])
    result_data.append([time_str, 'Household Washing Machines', row.iloc[9], row.iloc[10], row.iloc[11], row.iloc[12]])

# Create result DataFrame
result_df = pd.DataFrame(result_data, columns=columns)

# Save to Excel
output_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx"
result_df.to_excel(output_path, index=False)

print(f"Transformation complete!")
print(f"Output saved to: Processed.xlsx")
print(f"Result shape: {result_df.shape}")
print(f"First 10 rows:")
print(result_df.head(10).to_string())