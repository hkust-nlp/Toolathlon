import pandas as pd

file_path = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-excel-data-transformation/workspace/Household_Appliances.xlsx"

# Read with header=[0,1] to handle multi-level headers
try:
    df = pd.read_excel(file_path, header=[0, 1])
    print("Multi-header shape:", df.shape)
    print("Column levels:")
    print(df.columns.tolist()[:10])
except:
    # If multi-header doesn't work, read normally and process manually
    df = pd.read_excel(file_path)
    print("Regular read shape:", df.shape)
    
    # Extract the sub-headers from the first row
    sub_headers = df.iloc[0].tolist()
    print("Sub-headers:", sub_headers[:10])
    
    # Remove the first row and reset index
    df_clean = df.iloc[1:].reset_index(drop=True)
    print("Clean data shape:", df_clean.shape)
    print("Sample clean data:")
    print(df_clean.head(3))