# Let's examine the data more carefully
print("Sample of transformed data:")
print(result_df.head(15).to_string())

# Check the unique appliance types
print(f"\nUnique appliance types:")
print(result_df['Appliance types'].unique())

# Check some statistics
print(f"\nNon-null counts by column:")
print(result_df.count())

# Let's also check a few specific rows from the original data to verify transformation
print(f"\nOriginal data row 2 (first data row):")
print(df_raw.iloc[2, :13].tolist())

print(f"\nCorresponding transformed rows (first 3 rows for 2025-03-01):")
march_2025_data = result_df[result_df['Time'] == '2025-03-01']
print(march_2025_data.to_string())