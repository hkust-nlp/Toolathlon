import pandas as pd

# Read the original data with proper header handling
file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# It looks like the first row contains subheaders, let's read it properly
df_raw = pd.read_excel(file_path, header=[0, 1])
print("Multi-level header structure:")
print(df_raw.columns.tolist()[:10])  # Show first 10 columns

# Let's also try reading without multi-level headers
df = pd.read_excel(file_path, header=0)
print("\nSingle header structure:")
print(df.columns.tolist())

# Check the actual data starting from row with valid dates
df_clean = df[df['Time'].notna()].copy()
print(f"\nClean data shape: {df_clean.shape}")
print("\nFirst few rows of clean data:")
print(df_clean.head(3))