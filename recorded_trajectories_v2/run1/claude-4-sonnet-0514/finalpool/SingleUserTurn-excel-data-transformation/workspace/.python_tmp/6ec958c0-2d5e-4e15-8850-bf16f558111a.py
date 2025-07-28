# Let's look at the first few rows and columns more systematically
print("First 5 rows, first 10 columns:")
print(df_raw.iloc[:5, :10])
print("\nFirst 5 rows, columns 10-17:")
print(df_raw.iloc[:5, 10:18])

# Let's also check the header rows
print("\nFirst 3 rows (likely headers):")
for i in range(3):
    print(f"Row {i}:", df_raw.iloc[i].tolist())