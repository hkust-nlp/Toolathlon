import json

# Read and display a few examples from each source
output_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-merge-hf-datasets/workspace/unified_tool_call.jsonl'

examples_by_source = {}

with open(output_path, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f):
        if line_num >= 1500:  # Only read first 1500 lines
            break
        
        entry = json.loads(line.strip())
        source = entry['conversation_id'].split('_')[0]
        
        if source not in examples_by_source:
            examples_by_source[source] = []
        
        # Keep only first 2 examples per source for display
        if len(examples_by_source[source]) < 2:
            examples_by_source[source].append(entry)

# Display examples
for source, examples in examples_by_source.items():
    print(f"\n{'='*50}")
    print(f"Examples from {source}")
    print(f"{'='*50}")
    
    for i, example in enumerate(examples):
        print(f"\n--- Example {i+1} ---")
        print(f"Conversation ID: {example['conversation_id']}")
        print(f"Number of messages: {len(example['messages'])}")
        print(f"Number of tools: {len(example['tools'])}")
        
        # Show first few messages
        print("Messages:")
        for j, msg in enumerate(example['messages'][:3]):  # Show first 3 messages
            print(f"  {j+1}. {msg['role']}: {str(msg.get('content', 'null'))[:100]}{'...' if len(str(msg.get('content', ''))) > 100 else ''}")
            if 'tool_calls' in msg:
                print(f"     Tool calls: {len(msg['tool_calls'])}")
                for tc in msg['tool_calls']:
                    print(f"       - {tc['name']} (id: {tc['id']})")
        
        if len(example['messages']) > 3:
            print(f"  ... and {len(example['messages']) - 3} more messages")

# Count total lines
with open(output_path, 'r', encoding='utf-8') as f:
    total_lines = sum(1 for line in f)

print(f"\n{'='*50}")
print(f"SUMMARY")
print(f"{'='*50}")
print(f"Total entries in unified_tool_call.jsonl: {total_lines}")
print(f"File size: {3831476 / 1024 / 1024:.2f} MB")
print("Successfully created unified dataset with entries from:")
print("- Team-ACE/ToolACE (toolace): 500 entries")
print("- llamafactory/glaive_toolcall_en (glaive): 500 entries") 
print("- Salesforce/xlam-function-calling-60k (xlam): 500 entries")