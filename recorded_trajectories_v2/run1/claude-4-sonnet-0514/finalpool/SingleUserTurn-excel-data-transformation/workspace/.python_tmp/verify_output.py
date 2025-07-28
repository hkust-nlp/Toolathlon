import pandas as pd

# Read both files to compare structure
example_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx"
processed_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx"

example_df = pd.read_excel(example_path)
processed_df = pd.read_excel(processed_path)

print("=== FORMAT COMPARISON ===")
print(f"Example file columns: {example_df.columns.tolist()}")
print(f"Processed file columns: {processed_df.columns.tolist()}")
print(f"Columns match: {list(example_df.columns) == list(processed_df.columns)}")

print(f"\nExample file shape: {example_df.shape}")
print(f"Processed file shape: {processed_df.shape}")

print(f"\nExample appliance types: {example_df['Appliance types'].unique()}")
print(f"Processed appliance types: {processed_df['Appliance types'].unique()}")

print(f"\n=== SAMPLE DATA COMPARISON ===")
print("Example data (first 6 rows):")
print(example_df)

print("\nProcessed data (first 6 rows):")
print(processed_df.head(6))

print(f"\n=== SUMMARY ===")
print(f"✓ Successfully transformed {processed_df.shape[0]} rows of data")
print(f"✓ Data covers {processed_df['Time'].nunique()} unique time periods")
print(f"✓ Data includes 3 appliance types: {', '.join(processed_df['Appliance types'].unique())}")
print(f"✓ Output file saved as: Processed.xlsx")