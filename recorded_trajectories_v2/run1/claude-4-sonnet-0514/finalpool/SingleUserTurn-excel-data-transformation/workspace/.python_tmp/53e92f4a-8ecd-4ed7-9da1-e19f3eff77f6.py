# Verify the output file and compare with format example
import pandas as pd

# Read the processed file
processed_df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx')

# Read the format example
example_df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')

print("=== FORMAT EXAMPLE ===")
print(f"Shape: {example_df.shape}")
print(f"Columns: {example_df.columns.tolist()}")
print(example_df.head())

print("\n=== PROCESSED DATA ===")
print(f"Shape: {processed_df.shape}")
print(f"Columns: {processed_df.columns.tolist()}")
print(processed_df.head())

print("\n=== COLUMN COMPARISON ===")
print("Format Example columns:", example_df.columns.tolist())
print("Processed Data columns:", processed_df.columns.tolist())
print("Columns match:", example_df.columns.tolist() == processed_df.columns.tolist())

print("\n=== DATA SUMMARY ===")
print(f"Total records in processed data: {len(processed_df)}")
print(f"Unique time periods: {processed_df['Time'].nunique()}")
print(f"Unique appliance types: {processed_df['Appliance types'].unique()}")

# Show distribution by appliance type
print("\n=== RECORDS BY APPLIANCE TYPE ===")
print(processed_df['Appliance types'].value_counts())

# Show time range
print(f"\n=== TIME RANGE ===")
print(f"From: {processed_df['Time'].min()} to {processed_df['Time'].max()}")