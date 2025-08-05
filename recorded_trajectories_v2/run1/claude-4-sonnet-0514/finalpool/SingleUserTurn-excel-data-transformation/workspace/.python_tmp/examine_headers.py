print("First few rows with all columns:")
for i in range(3):
    print(f"Row {i}:")
    for j in range(18):
        print(f"  Col {j}: {df_raw.iloc[i, j]}")
    print()