import pandas as pd

# Read and process the data efficiently
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

df = pd.read_excel(file_path)
df_data = df.iloc[1:].copy()  # Remove header row
df_data = df_data.dropna(subset=[df_data.columns[0]])  # Remove rows with no time data

# Rename columns for easier access
df_data.columns = [
    'Time', 
    'Ref_Current', 'Ref_Accumulated', 'Ref_YearGrowth', 'Ref_AccGrowth',
    'AC_Current', 'AC_Accumulated', 'AC_YearGrowth', 'AC_AccGrowth', 
    'WM_Current', 'WM_Accumulated', 'WM_YearGrowth', 'WM_AccGrowth'
] + list(df_data.columns[13:])

# Create three separate DataFrames for each appliance
refrigerator_df = df_data[['Time', 'Ref_Current', 'Ref_Accumulated', 'Ref_YearGrowth', 'Ref_AccGrowth']].copy()
refrigerator_df['Appliance types'] = 'Household Refrigerator'

aircon_df = df_data[['Time', 'AC_Current', 'AC_Accumulated', 'AC_YearGrowth', 'AC_AccGrowth']].copy()
aircon_df['Appliance types'] = 'Air Conditioner'

washingmachine_df = df_data[['Time', 'WM_Current', 'WM_Accumulated', 'WM_YearGrowth', 'WM_AccGrowth']].copy()
washingmachine_df['Appliance types'] = 'Household Washing Machines'

# Rename columns to standard names
standard_columns = {
    'Ref_Current': 'Current Period Sales(Ten Thousand Units)',
    'Ref_Accumulated': 'Accumulated Sales (Ten Thousand Units)',
    'Ref_YearGrowth': 'Year-on-Year Growth (%)',
    'Ref_AccGrowth': 'Accumulated Growth (%)',
    'AC_Current': 'Current Period Sales(Ten Thousand Units)',
    'AC_Accumulated': 'Accumulated Sales (Ten Thousand Units)',
    'AC_YearGrowth': 'Year-on-Year Growth (%)',
    'AC_AccGrowth': 'Accumulated Growth (%)',
    'WM_Current': 'Current Period Sales(Ten Thousand Units)',
    'WM_Accumulated': 'Accumulated Sales (Ten Thousand Units)',
    'WM_YearGrowth': 'Year-on-Year Growth (%)',
    'WM_AccGrowth': 'Accumulated Growth (%)'
}

refrigerator_df.rename(columns=standard_columns, inplace=True)
aircon_df.rename(columns=standard_columns, inplace=True)
washingmachine_df.rename(columns=standard_columns, inplace=True)

print("Processing complete!")
print(f"Refrigerator data shape: {refrigerator_df.shape}")
print(f"Air conditioner data shape: {aircon_df.shape}")
print(f"Washing machine data shape: {washingmachine_df.shape}")

# Show sample
print("\nSample refrigerator data:")
print(refrigerator_df.head(3))