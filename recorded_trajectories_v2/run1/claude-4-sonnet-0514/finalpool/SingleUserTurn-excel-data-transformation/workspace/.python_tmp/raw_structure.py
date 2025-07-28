import pandas as pd

# Read the Excel file with no header to see the raw structure
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"
df_raw = pd.read_excel(file_path, header=None)

print("Raw data structure (first 8 rows, first 12 columns):")
for i in range(min(8, len(df_raw))):
    row_data = []
    for j in range(min(12, len(df_raw.columns))):
        val = df_raw.iloc[i, j]
        if pd.isna(val):
            row_data.append("NaN")
        else:
            row_data.append(str(val)[:20])  # Truncate long strings
    print(f"Row {i}: {row_data}")

print(f"\nTotal shape: {df_raw.shape}")