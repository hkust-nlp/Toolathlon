# Save the transformed data to a new Excel file
output_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'

# Save to Excel
result_df.to_excel(output_path, index=False)

print(f"Successfully saved transformed data to: {output_path}")
print(f"Final dataset shape: {result_df.shape}")
print(f"Columns: {list(result_df.columns)}")

# Show a summary of the final data
print(f"\nFinal data summary:")
print(f"- Total rows: {len(result_df)}")
print(f"- Time periods: {result_df['Time'].nunique()}")
print(f"- Appliance types: {result_df['Appliance types'].nunique()}")
print(f"- Date range: {result_df['Time'].min()} to {result_df['Time'].max()}")

# Show the last few rows to verify
print(f"\nLast 10 rows of the transformed data:")
print(result_df.tail(10).to_string())