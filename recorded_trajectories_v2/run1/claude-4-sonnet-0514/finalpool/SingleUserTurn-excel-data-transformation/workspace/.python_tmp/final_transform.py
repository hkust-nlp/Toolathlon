import pandas as pd
import numpy as np

# Read the Excel file
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"
df_raw = pd.read_excel(file_path, header=None)

# Extract data starting from row 2
data_rows = df_raw.iloc[2:].copy()
data_rows = data_rows[data_rows.iloc[:, 0].notna()]  # Remove rows with NaN time

# Define the three appliance types and their column ranges
appliances = [
    ('Household Refrigerators', 1, 5),  # columns 1-4
    ('Air Conditioners', 5, 9),         # columns 5-8
    ('Household Washing Machines', 9, 13) # columns 9-12
]

# Create the transformed data
transformed_data = []

for _, row in data_rows.iterrows():
    time_val = row.iloc[0]
    
    for appliance_name, start_col, end_col in appliances:
        # Extract the four metrics for this appliance
        current_sales = row.iloc[start_col] if start_col < len(row) else np.nan
        accumulated_sales = row.iloc[start_col + 1] if start_col + 1 < len(row) else np.nan
        yoy_growth = row.iloc[start_col + 2] if start_col + 2 < len(row) else np.nan
        accumulated_growth = row.iloc[start_col + 3] if start_col + 3 < len(row) else np.nan
        
        # Only add rows that have at least some data
        if not all(pd.isna([current_sales, accumulated_sales, yoy_growth, accumulated_growth])):
            transformed_data.append({
                'Time': time_val,
                'Appliance types': appliance_name,
                'Current Period Sales(Ten Thousand Units)': current_sales,
                'Accumulated Sales (Ten Thousand Units)': accumulated_sales,
                'Year-on-Year Growth (%)': yoy_growth * 100 if pd.notna(yoy_growth) else np.nan,  # Convert to percentage
                'Accumulated Growth (%)': accumulated_growth * 100 if pd.notna(accumulated_growth) else np.nan  # Convert to percentage
            })

# Create the transformed DataFrame
transformed_df = pd.DataFrame(transformed_data)

# Format the Time column to show only YYYY-MM
transformed_df['Time'] = pd.to_datetime(transformed_df['Time']).dt.strftime('%Y-%m')

# Sort by Time and Appliance types for better organization
transformed_df = transformed_df.sort_values(['Time', 'Appliance types']).reset_index(drop=True)

# Save to Excel file
output_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx"
transformed_df.to_excel(output_path, index=False)

print("Data transformation completed successfully!")
print(f"Output saved to: Processed.xlsx")
print(f"Total records: {len(transformed_df)}")
print(f"Time period: {transformed_df['Time'].min()} to {transformed_df['Time'].max()}")
print(f"Appliance types: {list(transformed_df['Appliance types'].unique())}")

# Show a sample of the final data
print("\nSample of the transformed data:")
print(transformed_df.head(9))  # Show 3 records for each appliance type