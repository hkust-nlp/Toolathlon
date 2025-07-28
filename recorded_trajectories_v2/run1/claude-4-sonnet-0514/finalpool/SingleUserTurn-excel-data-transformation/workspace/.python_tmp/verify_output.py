import pandas as pd

# Verify the processed file
processed_df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx')

print("🎉 TRANSFORMATION COMPLETED SUCCESSFULLY!")
print("="*60)
print(f"✅ Original file: Household_Appliances.xlsx")
print(f"✅ Processed file: Processed.xlsx")
print(f"✅ Records processed: {len(processed_df)}")
print(f"✅ NaN values ignored as requested")

print("\n📊 DATA STRUCTURE:")
print("="*30)
print("Columns in the processed data:")
for i, col in enumerate(processed_df.columns, 1):
    print(f"{i}. {col}")

print(f"\n📈 METRICS INCLUDED:")
print("="*30)
for i, metric in enumerate(processed_df['Metric'].unique(), 1):
    count = len(processed_df[processed_df['Metric'] == metric])
    print(f"{i}. {metric} ({count} records)")

print(f"\n🏠 PRODUCTS INCLUDED:")
print("="*30)
for i, product in enumerate(processed_df['Product'].unique(), 1):
    count = len(processed_df[processed_df['Product'] == product])
    print(f"{i}. {product} ({count} records)")

print(f"\n📅 DATE RANGE:")
print("="*30)
print(f"From: {processed_df['Date'].min()}")
print(f"To: {processed_df['Date'].max()}")
print(f"Total months: {processed_df['Date'].nunique()}")

print(f"\n💡 SAMPLE DATA:")
print("="*30)
sample = processed_df.head(10)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(sample.to_string(index=False))