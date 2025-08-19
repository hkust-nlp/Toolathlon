# Now let's extract the data and calculate the Appliance category values
print("Processing Appliance category conversion...")

# Get the years from raw data (starting from row 4, column 0)
years = []
appliance_values = []

# Extract years and calculate appliance values for each year
for row_idx in range(4, len(raw_data_df)):
    year = raw_data_df.iloc[row_idx, 0]
    if pd.notna(year) and isinstance(year, (int, float)):
        years.append(int(year))
        
        # Calculate appliance value based on methodology:
        # Appliance: [(7, 0.5), (10, 0.2), (11, 0.3)]
        # This means: Electric * 0.5 + Furniture * 0.2 + Construction * 0.3
        
        electric_value = raw_data_df.iloc[row_idx, 7]  # Column 7 is Electric (index 6+1)
        furniture_value = raw_data_df.iloc[row_idx, 10]  # Column 10 is Furniture (index 9+1)
        construction_value = raw_data_df.iloc[row_idx, 11]  # Column 11 is Construction (index 10+1)
        
        # Handle missing values
        electric_value = 0 if pd.isna(electric_value) else electric_value
        furniture_value = 0 if pd.isna(furniture_value) else furniture_value
        construction_value = 0 if pd.isna(construction_value) else construction_value
        
        appliance_value = (electric_value * 0.5 + 
                          furniture_value * 0.2 + 
                          construction_value * 0.3)
        
        appliance_values.append(appliance_value)
        print(f"Year {year}: Electric={electric_value}, Furniture={furniture_value}, Construction={construction_value}, Appliance={appliance_value}")

print(f"\nYears: {years}")
print(f"Appliance values: {appliance_values}")