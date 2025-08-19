# Create the Excel file with the results
output_file = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-market-research/workspace/growth_rate.xlsx'

# Create a new workbook
wb = Workbook()
ws = wb.active
ws.title = "Growth Rate Analysis"

# Add headers
headers = ['Year', 'Electric %', 'Construction %', 'Furniture %', 'Growth Rate %']
for col, header in enumerate(headers, 1):
    ws.cell(row=1, column=col, value=header)

# Add data
for row_idx, (_, row_data) in enumerate(results_df.iterrows(), 2):
    for col_idx, value in enumerate(row_data, 1):
        if pd.isna(value):
            ws.cell(row=row_idx, column=col_idx, value=None)
        else:
            ws.cell(row=row_idx, column=col_idx, value=value)

# Save the workbook
wb.save(output_file)
print(f"Excel file saved as: {output_file}")

# Verify the file can be loaded with load_workbook(file_path, data_only=True)
try:
    test_wb = load_workbook(output_file, data_only=True)
    print("✓ File can be loaded with load_workbook(file_path, data_only=True)")
    
    # Show the data
    test_ws = test_wb.active
    print("\nFile contents verification:")
    for row in test_ws.iter_rows(max_row=11, values_only=True):
        print(row)
        
    test_wb.close()
except Exception as e:
    print(f"✗ Error loading file: {e}")

print("\nSummary:")
print(f"- Processed Appliance category data from 2015 to 2024")
print(f"- Appliance category is calculated as: Electric * 0.5 + Furniture * 0.2 + Construction * 0.3")
print(f"- Annual growth rates calculated for each year from 2015 to 2024")
print(f"- Highest growth rate: {max([g for g in growth_rates if g is not None]):.2f}% (2019 to 2020)")
print(f"- Output file: {output_file}")