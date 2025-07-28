# Clean up the data and save to Excel
import pandas as pd
import numpy as np

# Read the data
df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

# Extract data starting from row 4 (where actual data begins)
data_start_row = 4
main_data = df.iloc[data_start_row:].reset_index(drop=True)

# Extract time column (column 0) - remove NaN values
time_data = main_data.iloc[:, 0].dropna().reset_index(drop=True)

# Extract data for each appliance type
refrigerator_data = main_data.iloc[:len(time_data), 1:5]
air_conditioner_data = main_data.iloc[:len(time_data), 5:9]
washing_machine_data = main_data.iloc[:len(time_data), 9:13]

# Create the transformed data
transformed_data = []

# Column names for the output based on the format example
output_columns = [
    'Time',
    'Appliance types', 
    'Current Period Sales(Ten Thousand Units)',
    'Accumulated Sales (Ten Thousand Units)',
    'Year-on-Year Growth (%)',
    'Accumulated Growth (%)'
]

# Process each appliance type
appliance_types = ['Household Refrigerators', 'Air Conditioners', 'Household Washing Machines']
data_sections = [refrigerator_data, air_conditioner_data, washing_machine_data]

for appliance_type, data_section in zip(appliance_types, data_sections):
    for i in range(len(time_data)):
        # Skip rows where all data is NaN
        row_data = data_section.iloc[i]
        if not row_data.isna().all():
            transformed_row = [
                time_data.iloc[i],
                appliance_type,
                row_data.iloc[0],  # Current Period Sales
                row_data.iloc[1],  # Accumulated Sales
                row_data.iloc[2],  # Year-on-Year Growth
                row_data.iloc[3]   # Accumulated Growth
            ]
            transformed_data.append(transformed_row)

# Create the final DataFrame
result_df = pd.DataFrame(transformed_data, columns=output_columns)

# Remove rows with NaN values in critical columns
result_df = result_df.dropna(subset=['Current Period Sales(Ten Thousand Units)', 'Accumulated Sales (Ten Thousand Units)'])

# Format the Time column to show only year-month
result_df['Time'] = pd.to_datetime(result_df['Time']).dt.strftime('%Y-%m')

# Sort by time and appliance type for better organization
result_df = result_df.sort_values(['Time', 'Appliance types']).reset_index(drop=True)

print(f"Final transformed data shape: {result_df.shape}")
print("\nFirst 15 rows of final data:")
print(result_df.head(15))

# Save to Excel file
output_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'
result_df.to_excel(output_path, index=False)

print(f"\nData successfully saved to: {output_path}")
print(f"Total records: {len(result_df)}")

# Show sample of each appliance type
print("\nSample data for each appliance type:")
for appliance in appliance_types:
    sample = result_df[result_df['Appliance types'] == appliance].head(3)
    print(f"\n{appliance}:")
    print(sample)