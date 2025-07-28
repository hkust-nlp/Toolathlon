import pandas as pd

# Simple approach - read and check basic info
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

df = pd.read_excel(file_path)
print("Original shape:", df.shape)

# Remove first row and get clean data
clean_data = []
for i in range(1, min(6, len(df))):  # Process just first 5 data rows
    row = df.iloc[i]
    time_val = row.iloc[0]
    
    if pd.notna(time_val):
        # Format time as YYYY-MM
        time_str = time_val.strftime('%Y-%m')
        
        # Add three rows for three appliances
        clean_data.append([time_str, 'Household Refrigerator', row.iloc[1], row.iloc[2], row.iloc[3], row.iloc[4]])
        clean_data.append([time_str, 'Air Conditioner', row.iloc[5], row.iloc[6], row.iloc[7], row.iloc[8]])
        clean_data.append([time_str, 'Household Washing Machines', row.iloc[9], row.iloc[10], row.iloc[11], row.iloc[12]])

# Create result DataFrame
columns = ['Time', 'Appliance types', 'Current Period Sales(Ten Thousand Units)', 
          'Accumulated Sales (Ten Thousand Units)', 'Year-on-Year Growth (%)', 'Accumulated Growth (%)']
result_df = pd.DataFrame(clean_data, columns=columns)

print("Sample transformed data:")
print(result_df)