import pandas as pd
import numpy as np

# Read the Excel file
df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

# Remove the first row which contains sub-headers
df_clean = df.iloc[1:].copy()
df_clean = df_clean.reset_index(drop=True)

# Define the structure
products = [
    'Household Refrigerators',
    'Air Conditioners', 
    'Household Washing Machines'
]

metrics = [
    'Current Period Sales (Ten Thousand Units)',
    'Accumulated Sales (Ten Thousand Units)',
    'Year-on-Year Growth (%)',
    'Accumulated Growth (%)'
]

# Create the one-dimensional format
result_data = []

# Process main data section (columns 1-12)
for row_idx, row in df_clean.iterrows():
    date = row['Time']
    if pd.isna(date):
        continue
        
    for prod_idx, product in enumerate(products):
        base_col = 1 + prod_idx * 4  # Starting column for each product
        
        for metric_idx, metric in enumerate(metrics):
            col_idx = base_col + metric_idx
            value = row.iloc[col_idx]
            
            # Skip NaN values as requested
            if pd.isna(value):
                continue
                
            # Try to convert to numeric if it's a string representation of a number
            if isinstance(value, str):
                try:
                    value = float(value)
                except:
                    continue
            
            result_data.append({
                'Date': date,
                'Product': product,
                'Metric': metric,
                'Value': value
            })

# Process summary section (columns 14-17) - Accumulated Growth data
for row_idx, row in df_clean.iterrows():
    date = row.iloc[14]  # Accumulated Growth(%) column contains dates
    if pd.isna(date):
        continue
        
    # The summary section has accumulated growth data for each product
    summary_products = ['Household Refrigerators', 'Air Conditioners', 'Household Washing Machines']
    summary_cols = [15, 16, 17]  # Unnamed columns with the growth data
    
    for prod_idx, product in enumerate(summary_products):
        value = row.iloc[summary_cols[prod_idx]]
        
        # Skip NaN values as requested
        if pd.isna(value):
            continue
            
        # Try to convert to numeric if it's a string representation of a number
        if isinstance(value, str):
            try:
                value = float(value)
            except:
                continue
        
        result_data.append({
            'Date': date,
            'Product': product,
            'Metric': 'Summary Accumulated Growth (%)',
            'Value': value
        })

# Create the final DataFrame
result_df = pd.DataFrame(result_data)

# Sort by Date and Product for better organization
result_df = result_df.sort_values(['Date', 'Product', 'Metric']).reset_index(drop=True)

# Save to Excel file
output_path = '/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx'
result_df.to_excel(output_path, index=False)

print("✅ Successfully saved the transformed data to 'Processed.xlsx'")
print(f"📊 Final dataset contains {len(result_df)} records")
print(f"📅 Date range: {result_df['Date'].min()} to {result_df['Date'].max()}")
print(f"🏠 Products: {', '.join(result_df['Product'].unique())}")
print(f"📈 Metrics: {len(result_df['Metric'].unique())} different metrics")

print("\nSample of the final transformed data:")
print(result_df.head(15))