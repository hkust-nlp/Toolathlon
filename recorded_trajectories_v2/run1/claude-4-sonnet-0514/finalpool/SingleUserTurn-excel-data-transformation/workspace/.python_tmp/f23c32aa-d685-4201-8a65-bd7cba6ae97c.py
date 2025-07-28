import pandas as pd
import numpy as np

# Verify the created file by reading it back
verification_df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx')

print("Verification - Reading back the created Processed.xlsx file:")
print(f"Shape: {verification_df.shape}")
print(f"Columns: {list(verification_df.columns)}")

print("\nFirst 10 rows:")
print(verification_df.head(10).to_string())

print("\nSample of data with non-null values:")
non_null_sample = verification_df.dropna(subset=['Current Period Sales(Ten Thousand Units)']).head(10)
print(non_null_sample.to_string())

print(f"\nData types:")
print(verification_df.dtypes)

# Check that NaN values are preserved
print(f"\nNaN preservation check:")
print(f"Total NaN values in Current Period Sales: {verification_df['Current Period Sales(Ten Thousand Units)'].isna().sum()}")
print(f"Total NaN values in Accumulated Sales: {verification_df['Accumulated Sales (Ten Thousand Units)'].isna().sum()}")
print(f"Total NaN values in Year-on-Year Growth: {verification_df['Year-on-Year Growth (%)'].isna().sum()}")
print(f"Total NaN values in Accumulated Growth: {verification_df['Accumulated Growth (%)'].isna().sum()}")