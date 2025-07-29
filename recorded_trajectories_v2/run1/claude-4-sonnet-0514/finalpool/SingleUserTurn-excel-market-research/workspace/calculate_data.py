# Process market data conversion
# From methodology analysis:
# Appliance category = Electric * 0.5 + Furniture * 0.2 + Construction * 0.3

# Raw data columns (from RawData sheet):
# B=Agriculture, C=Oil&Gas, D=Food, E=Metals, F=Electronic, G=Electric, 
# H=Auto Production, I=Transportation, J=Furniture, K=Construction, L=Industry, 
# M=Steel Production, N=Air Bus, O=Boeing, P=MRO

# Years 2014-2032 data from the RawData sheet
years_data = [
    # Year, Electric(G), Furniture(J), Construction(K in bn USD)
    [2014, 342107.7191625384, 42050.906588215, 5.319836457699379],
    [2015, 358552.41150796344, 44111.78030022254, 5.592572143500352],
    [2016, 379331.34470816527, 46420.701662578394, 5.921518759207255],
    [2017, 411597.7359131227, 49469.57275245701, 6.166446582962583],
    [2018, 434236.0045253139, 51479.91710742547, 6.423278390430157],
    [2019, 463602.6703354453, 52813.74177530104, 6.654481282157320],
    [2020, 486220.6809761241, 50442.6519447534, 6.788058172718769],
    [2021, 557979.077, 55034.405999999995, 6.847533906979786],
    [2022, 610144.5085840949, 52525.924627890534, 7.095334934747884],
    [2023, 670492.8028372353, 49611.85590582785, 7.319210194782733],
    [2024, 697769.4810775969, 51261.286177829, 7.434286931356872],
    [2025, 731056.2160414273, 52189.60057585256, 7.625782686042930],
    [2026, 768912.3059558865, 53113.534848133946, 7.895522719922827],
    [2027, 809438.8541458189, 54059.7080299556, 8.194499467539080],
    [2028, 852124.2415253158, 55125.67903086003, 8.500326473000172],
    [2029, 896362.1264795316, 56254.93192363136, 8.807592258577573],
    [2030, 942852.7030861316, 57347.63350540321, 9.125114175681421],
    [2031, 991839.83425363, 58597.95340614477, 9.450394633585460],
    [2032, 1043792.4099735507, 59959.011492764446, 9.786894639457943]
]

# Calculate appliance values and components
results = []
appliance_values = []

for i, (year, electric, furniture, construction_bn) in enumerate(years_data):
    # Convert Construction from bn USD to mn USD
    construction_mn = construction_bn * 1000
    
    # Calculate total appliance value
    appliance_total = electric * 0.5 + furniture * 0.2 + construction_mn * 0.3
    appliance_values.append(appliance_total)
    
    # Calculate components for output (based on format example)
    electric_component = electric * 0.5  # 50% of Electric
    construction_component = construction_mn * 0.3  # 30% of Construction
    furniture_component = furniture * 0.2  # 20% of Furniture
    
    # Calculate growth rate (except for first year)
    if i == 0:
        growth_rate = None  # No growth rate for first year
    else:
        growth_rate = (appliance_values[i] - appliance_values[i-1]) / appliance_values[i-1] * 100
    
    results.append([year, electric_component, construction_component, furniture_component, growth_rate])

print("Processed data:")
for i, row in enumerate(results[:5]):  # Show first 5 rows
    print(f"Row {i+1}: {row}")

print(f"\nTotal appliance values for first 5 years:")
for i in range(5):
    print(f"Year {years_data[i][0]}: {appliance_values[i]:.2f}")

# Write to file
with open('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-market-research/workspace/processed_data.txt', 'w') as f:
    f.write("Year,Electric_50%,Construction_30%,Furniture_20%,Growth_Rate\n")
    for row in results:
        if row[4] is None:
            f.write(f"{row[0]},{row[1]:.2f},{row[2]:.2f},{row[3]:.2f},\n")
        else:
            f.write(f"{row[0]},{row[1]:.2f},{row[2]:.2f},{row[3]:.2f},{row[4]:.2f}\n")

print("Data written to processed_data.txt")