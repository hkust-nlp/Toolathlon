import pandas as pd

# Read the processed file to verify it was saved correctly
df_processed_verify = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Processed.xlsx')

print("Verification of saved file:")
print(f"Shape: {df_processed_verify.shape}")
print("\nColumn names:")
print(df_processed_verify.columns.tolist())
print("\nFirst 10 rows:")
print(df_processed_verify.head(10))

# Compare with format example
df_example = pd.read_excel('/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Format_Example.xlsx')

print("\n" + "="*50)
print("COMPARISON WITH FORMAT EXAMPLE:")
print("="*50)
print("Format Example columns:", df_example.columns.tolist())
print("Processed file columns:", df_processed_verify.columns.tolist())
print("Columns match:", df_example.columns.tolist() == df_processed_verify.columns.tolist())

print("\nFormat Example appliance types:", df_example['Appliance types'].unique())
print("Processed file appliance types:", df_processed_verify['Appliance types'].unique())

print("\nSample comparison:")
print("Format Example:")
print(df_example.head(3))
print("\nProcessed file:")
print(df_processed_verify.head(3))