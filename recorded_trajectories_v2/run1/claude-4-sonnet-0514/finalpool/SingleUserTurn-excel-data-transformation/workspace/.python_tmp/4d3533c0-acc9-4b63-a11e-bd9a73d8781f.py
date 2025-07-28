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

print(f"\nSummary statistics for numerical columns:")
print(verification_df.describe())