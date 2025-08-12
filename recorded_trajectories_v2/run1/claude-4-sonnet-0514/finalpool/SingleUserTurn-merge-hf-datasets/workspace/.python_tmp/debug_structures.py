# Let me examine the XLAM dataset structure more carefully
import json
from datasets import load_dataset
from huggingface_hub import login

with open('/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-merge-hf-datasets/workspace/hf_token.txt', 'r') as f:
    token = f.read().strip()
login(token=token)

# Load XLAM dataset to understand structure
dataset = load_dataset("Salesforce/xlam-function-calling-60k")
data = dataset['train']
first_example = data[0]

print("XLAM first example structure:")
for key, value in first_example.items():
    print(f"{key}: {type(value)} = {value}")
    if isinstance(value, list) and len(value) > 0:
        print(f"  First element type: {type(value[0])}")
        if isinstance(value[0], dict):
            print(f"  First element keys: {list(value[0].keys())}")

# Also check Glaive tools structure
print("\n" + "="*50)
dataset_glaive = load_dataset("llamafactory/glaive_toolcall_en")
data_glaive = dataset_glaive['train']
first_glaive = data_glaive[0]

print("Glaive tools structure:")
print(f"tools type: {type(first_glaive['tools'])}")
print(f"tools content: {first_glaive['tools']}")