import pandas as pd

# Verify the created file
output_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx"
verification_df = pd.read_excel(output_path)

print("Verification of Processed.xlsx:")
print(f"Shape: {verification_df.shape}")
print(f"Columns: {list(verification_df.columns)}")
print("\nFirst 10 rows:")
print(verification_df.head(10))

print("\nLast 5 rows:")
print(verification_df.tail(5))

print("\nData summary:")
print(f"Unique time periods: {verification_df['Time'].nunique()}")
print(f"Unique appliance types: {verification_df['Appliance types'].nunique()}")
print(f"Appliance types: {list(verification_df['Appliance types'].unique())}")

# Check for any missing data patterns
print(f"\nMissing data summary:")
print(verification_df.isnull().sum())