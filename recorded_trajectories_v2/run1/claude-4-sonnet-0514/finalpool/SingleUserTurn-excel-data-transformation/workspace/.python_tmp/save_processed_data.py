# Save the transformed data to Excel
output_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'

# Convert datetime to a more readable format
df_transformed['Time'] = pd.to_datetime(df_transformed['Time']).dt.strftime('%Y-%m-%d')

# Save to Excel
df_transformed.to_excel(output_path, index=False)

print(f"Processed data saved to: {output_path}")
print("\nFinal data summary:")
print(f"Total records: {len(df_transformed)}")
print(f"Date range: {df_transformed['Time'].min()} to {df_transformed['Time'].max()}")
print(f"Appliance types: {len(df_transformed['Appliance_Type'].unique())}")
print(f"Metrics per appliance: {len(df_transformed['Metric'].unique())}")

# Show a sample of the final data
print("\nSample of final transformed data:")
print(df_transformed.head(15))