# Let's understand the complete data structure and transform it
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
# Refrigerators: columns 1-4 (Current Period Sales, Accumulated Sales, Year-on-Year Growth, Accumulated Growth)
refrigerator_data = main_data.iloc[:len(time_data), 1:5]

# Air Conditioners: columns 5-8
air_conditioner_data = main_data.iloc[:len(time_data), 5:9]

# Washing Machines: columns 9-12
washing_machine_data = main_data.iloc[:len(time_data), 9:13]

print(f"Time data length: {len(time_data)}")
print(f"Refrigerator data shape: {refrigerator_data.shape}")
print(f"Air conditioner data shape: {air_conditioner_data.shape}")
print(f"Washing machine data shape: {washing_machine_data.shape}")

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

print(f"\nTransformed data shape: {result_df.shape}")
print("\nFirst 10 rows of transformed data:")
print(result_df.head(10))

print("\nLast 10 rows of transformed data:")
print(result_df.tail(10))