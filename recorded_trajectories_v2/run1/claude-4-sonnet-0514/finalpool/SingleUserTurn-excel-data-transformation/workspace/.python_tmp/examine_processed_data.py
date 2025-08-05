# Let's examine the data more closely and sort it properly
print("Sample of processed data:")
print(df_processed.head(15))

print("\nTime range:")
print(f"Earliest: {df_processed['Time'].min()}")
print(f"Latest: {df_processed['Time'].max()}")

print("\nCount by appliance type:")
print(df_processed['Appliance types'].value_counts())

# Sort the data by time and appliance type for better organization
df_processed_sorted = df_processed.sort_values(['Time', 'Appliance types'])

print("\nFirst 15 rows after sorting:")
print(df_processed_sorted.head(15))