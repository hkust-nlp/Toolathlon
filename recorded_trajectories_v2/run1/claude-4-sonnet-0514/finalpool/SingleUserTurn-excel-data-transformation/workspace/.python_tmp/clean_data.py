import pandas as pd

# Read the generated file to verify
output_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx"
result_df = pd.read_excel(output_path)

print(f"Generated file shape: {result_df.shape}")

# Check for rows with all NaN values in the data columns
data_columns = ['Current Period Sales(Ten Thousand Units)', 'Accumulated Sales (Ten Thousand Units)', 
               'Year-on-Year Growth (%)', 'Accumulated Growth (%)']

# Count rows with all NaN data
all_nan_mask = result_df[data_columns].isna().all(axis=1)
print(f"Rows with all NaN data: {all_nan_mask.sum()}")

# Remove rows with all NaN data
clean_df = result_df[~all_nan_mask].copy()
print(f"Clean data shape: {clean_df.shape}")

# Save the cleaned version
clean_df.to_excel(output_path, index=False)

print(f"\nFirst 15 rows of clean data:")
print(clean_df.head(15).to_string())

print(f"\nLast 10 rows of clean data:")
print(clean_df.tail(10).to_string())