import os
import json
from datasets import load_dataset
from huggingface_hub import login

# Read the token and login
with open('/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-merge-hf-datasets/workspace/hf_token.txt', 'r') as f:
    token = f.read().strip()

login(token=token)

# Dataset configurations
datasets_info = [
    {"id": "Team-ACE/ToolACE", "short_name": "toolace"},
    {"id": "llamafactory/glaive_toolcall_en", "short_name": "glaive"},
    {"id": "Salesforce/xlam-function-calling-60k", "short_name": "xlam"}
]

# Load datasets and examine their structure
for dataset_info in datasets_info:
    print(f"\n=== Loading {dataset_info['id']} ===")
    try:
        dataset = load_dataset(dataset_info['id'])
        print(f"Dataset keys: {list(dataset.keys())}")
        
        # Get the train split (or first available split)
        split_name = 'train' if 'train' in dataset else list(dataset.keys())[0]
        data = dataset[split_name]
        
        print(f"Number of examples in {split_name}: {len(data)}")
        print(f"Column names: {data.column_names}")
        
        # Show first example
        if len(data) > 0:
            first_example = data[0]
            print(f"First example keys: {list(first_example.keys())}")
            print(f"First example preview:")
            for key, value in first_example.items():
                if isinstance(value, str) and len(value) > 200:
                    print(f"  {key}: {value[:200]}...")
                else:
                    print(f"  {key}: {value}")
                    
    except Exception as e:
        print(f"Error loading {dataset_info['id']}: {e}")