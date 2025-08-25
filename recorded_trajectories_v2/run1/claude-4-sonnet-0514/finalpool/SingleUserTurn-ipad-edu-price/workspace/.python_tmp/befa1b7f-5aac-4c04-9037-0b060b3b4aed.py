import json
import os

# Prepare the result data
result_data = {
    "cheapest_region": "United States",
    "cheapest_total_price": "USD 1,018"
}

# Get the workspace directory and create the file path
workspace_dir = "/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-ipad-edu-price/workspace"
file_path = os.path.join(workspace_dir, "result.json")

# Write the result to the JSON file
with open(file_path, 'w') as f:
    json.dump(result_data, f, indent=2)

print(f"Result saved to: {file_path}")
print(f"Content: {json.dumps(result_data, indent=2)}")

# Verify the file was created
if os.path.exists(file_path):
    print("✓ File successfully created")
    with open(file_path, 'r') as f:
        content = f.read()
        print(f"File contents:\n{content}")
else:
    print("✗ File creation failed")