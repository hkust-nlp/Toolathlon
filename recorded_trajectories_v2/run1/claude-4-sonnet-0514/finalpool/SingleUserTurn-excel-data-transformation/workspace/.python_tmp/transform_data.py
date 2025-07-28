import pandas as pd
import numpy as np

# Read the Excel file
df = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx')

# Remove the first row which contains sub-headers
df_clean = df.iloc[1:].copy()

# Reset index
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

print("Transformation completed!")
print(f"Original data shape: {df.shape}")
print(f"Transformed data shape: {result_df.shape}")
print("\nFirst 20 rows of transformed data:")
print(result_df.head(20))

print("\nData types in transformed data:")
print(result_df.dtypes)

print("\nUnique products:")
print(result_df['Product'].unique())

print("\nUnique metrics:")
print(result_df['Metric'].unique())

print("\nValue statistics:")
print(result_df['Value'].describe())