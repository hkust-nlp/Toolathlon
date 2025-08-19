# Now let's analyze the methodology mapping
print("Methodology mapping analysis:")
print("Row 1 (market categories):", methodology_df.iloc[1, 1:].tolist())
print("Row 2 (data sources):", methodology_df.iloc[2, 1:].tolist())

# Company internal categories and their mappings
print("\nCompany internal categories and their mappings:")
for i in range(3, 13):  # Rows 4-13 contain the mappings
    internal_category = methodology_df.iloc[i, 1]
    if pd.notna(internal_category):
        mappings = methodology_df.iloc[i, 2:].tolist()
        non_null_mappings = [(j+2, val) for j, val in enumerate(mappings) if pd.notna(val) and val != 0]
        print(f"{internal_category}: {non_null_mappings}")