# Let's examine the data more carefully
print("First few rows with all columns:")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(df.head(10))

print("\n" + "="*100)
print("Let's look at the first row (which might contain headers):")
print(df.iloc[0])

print("\n" + "="*100)
print("Let's check if there are any patterns in the data:")
print("Non-null counts per column:")
for i, col in enumerate(df.columns):
    non_null_count = df[col].notna().sum()
    print(f"Column {i} ({col}): {non_null_count} non-null values")