# Calculate the annual growth rates for the Appliance category from 2015 to 2024
growth_rates = []

# Find the indices for years 2015-2024
start_idx = years.index(2015)
end_idx = years.index(2024)

print("Calculating annual growth rates for Appliance category (2015-2024):")
print(f"2015 value: {appliance_values[start_idx]}")
print(f"2024 value: {appliance_values[end_idx]}")

for i in range(start_idx, end_idx):
    current_year = years[i]
    next_year = years[i + 1]
    current_value = appliance_values[i]
    next_value = appliance_values[i + 1]
    
    if current_value != 0:
        growth_rate = ((next_value - current_value) / current_value) * 100
    else:
        growth_rate = 0
    
    growth_rates.append(growth_rate)
    print(f"{current_year} to {next_year}: {current_value:.2f} -> {next_value:.2f}, Growth: {growth_rate:.2f}%")

# Create the results DataFrame
results_data = []
for i in range(start_idx, end_idx + 1):
    year = years[i]
    electric_pct = electric_percentages[i]
    construction_pct = construction_percentages[i]
    furniture_pct = furniture_percentages[i]
    
    if i < end_idx:  # Growth rate for this year to next year
        growth_rate = growth_rates[i - start_idx]
    else:  # No growth rate for the last year
        growth_rate = None
    
    results_data.append([year, electric_pct, construction_pct, furniture_pct, growth_rate])

# Create DataFrame
results_df = pd.DataFrame(results_data, columns=['Year', 'Electric %', 'Construction %', 'Furniture %', 'Growth Rate %'])
print("\nResults DataFrame:")
print(results_df)