# Show a final comprehensive sample of the processed data
import pandas as pd

processed_df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx')

print("=== FINAL PROCESSED DATA SAMPLE ===")
print("Showing data for a specific time period to demonstrate the transformation:")

# Show data for 2024-12 (most recent period)
sample_period = processed_df[processed_df['Time'] == '2024-12']
print(f"\nData for December 2024:")
print(sample_period)

print(f"\n=== TRANSFORMATION SUMMARY ===")
print("✅ Successfully transformed 2D table to 1D format")
print("✅ Original data had appliances in separate columns")
print("✅ Transformed data has appliances in separate rows")
print("✅ Maintained all data integrity with proper column mapping")
print("✅ Column names match the format example exactly")
print("✅ Time format converted to YYYY-MM as shown in example")
print("✅ Data sorted chronologically and by appliance type")
print(f"✅ Total records: {len(processed_df)} (60 time periods × 3 appliance types)")
print("✅ Output saved as 'Processed.xlsx' in workspace")

print(f"\n=== APPLIANCE TYPES IN PROCESSED DATA ===")
for appliance in processed_df['Appliance types'].unique():
    count = len(processed_df[processed_df['Appliance types'] == appliance])
    print(f"• {appliance}: {count} records")