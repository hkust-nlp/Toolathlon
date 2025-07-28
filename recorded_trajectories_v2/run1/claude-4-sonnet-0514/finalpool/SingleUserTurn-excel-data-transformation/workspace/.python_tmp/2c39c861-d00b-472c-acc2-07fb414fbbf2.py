# Let's examine the data more carefully
print("Full data preview:")
print(df_original.to_string())
print("\n" + "="*50)

# Check if there are headers in the first few rows
print("\nFirst 10 rows:")
for i in range(min(10, len(df_original))):
    print(f"Row {i}: {df_original.iloc[i].tolist()}")