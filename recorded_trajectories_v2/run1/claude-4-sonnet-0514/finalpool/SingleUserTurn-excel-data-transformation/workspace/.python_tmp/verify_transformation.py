import pandas as pd

# Read the processed file to verify it was saved correctly
processed_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'
df_processed = pd.read_excel(processed_path)

print("TRANSFORMATION COMPLETE!")
print("="*60)
print("Original format: Two-dimensional table with appliances in separate columns")
print("New format: One-dimensional table with each row representing one data point")
print("="*60)

print(f"\nProcessed data structure:")
print(f"- Total records: {len(df_processed)}")
print(f"- Columns: {list(df_processed.columns)}")
print(f"- Date range: {df_processed['Time'].min()} to {df_processed['Time'].max()}")

print(f"\nAppliance types ({len(df_processed['Appliance_Type'].unique())}):")
for appliance in sorted(df_processed['Appliance_Type'].unique()):
    count = len(df_processed[df_processed['Appliance_Type'] == appliance])
    print(f"  - {appliance}: {count} records")

print(f"\nMetrics tracked ({len(df_processed['Metric'].unique())}):")
for metric in sorted(df_processed['Metric'].unique()):
    count = len(df_processed[df_processed['Metric'] == metric])
    print(f"  - {metric}: {count} records")

print(f"\nSample of transformed data (showing different appliances and metrics):")
print("-" * 80)
sample_data = df_processed.head(20)
for idx, row in sample_data.iterrows():
    print(f"{row['Time']} | {row['Appliance_Type']:<25} | {row['Metric']:<40} | {row['Value']}")

print(f"\nFile saved as: Processed.xlsx")
print("Transformation completed successfully!")