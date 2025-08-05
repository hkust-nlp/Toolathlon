# Let's look at rows 2-10 to understand the data pattern
print("Data rows 2-10:")
for i in range(2, 11):
    print(f"Row {i}: Time={df_raw.iloc[i, 0]}")
    print(f"  Refrigerators: {df_raw.iloc[i, 1:5].values}")
    print(f"  Air Conditioners: {df_raw.iloc[i, 5:9].values}")
    print(f"  Washing Machines: {df_raw.iloc[i, 9:13].values}")
    print(f"  Additional Growth: {df_raw.iloc[i, 15:18].values}")
    print()