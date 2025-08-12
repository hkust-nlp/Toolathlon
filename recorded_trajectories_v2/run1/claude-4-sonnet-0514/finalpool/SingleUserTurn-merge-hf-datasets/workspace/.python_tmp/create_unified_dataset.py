import json
import re
from datasets import load_dataset
from huggingface_hub import login

# Login
with open('/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-merge-hf-datasets/workspace/hf_token.txt', 'r') as f:
    token = f.read().strip()
login(token=token)

def convert_toolace_to_unified(example, index, source_name):
    """Convert ToolACE format to unified format"""
    conversation_id = f"{source_name}_{index}"
    
    messages = []
    tools = []
    tool_call_counter = 0
    
    # Parse system message - skip if it's just tool usage instructions
    system_content = example['system']
    if not ("composing functions" in system_content.lower() or "tool calls" in system_content.lower()):
        messages.append({
            "role": "system",
            "content": system_content
        })
    
    # Parse conversations
    conversations = example['conversations']
    
    for conv in conversations:
        if conv['from'] == 'user':
            messages.append({
                "role": "user",
                "content": conv['value']
            })
        elif conv['from'] == 'assistant':
            content = conv['value']
            
            # Check if this is a tool call (contains API calls in brackets)
            tool_call_pattern = r'\[([^\[\]]+)\]'
            tool_calls_found = re.findall(tool_call_pattern, content)
            
            if tool_calls_found and not any(char in content for char in ['{', '"results"']):
                # This is a tool call
                tool_calls = []
                for tool_call_str in tool_calls_found:
                    # Parse tool call like "Market Trends API(trend_type="MARKET_INDEXES", country="us")"
                    match = re.match(r'([^(]+)\((.+)\)', tool_call_str)
                    if match:
                        tool_name = match.group(1).strip()
                        args_str = match.group(2)
                        
                        # Simple argument parsing
                        arguments = {}
                        arg_matches = re.findall(r'(\w+)="([^"]*)"', args_str)
                        for arg_name, arg_value in arg_matches:
                            arguments[arg_name] = arg_value
                        
                        tool_calls.append({
                            "id": f"tool_call_{tool_call_counter}",
                            "name": tool_name,
                            "arguments": arguments
                        })
                        tool_call_counter += 1
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
            else:
                # Regular assistant message
                messages.append({
                    "role": "assistant",
                    "content": content
                })
        elif conv['from'] == 'tool':
            # Find the corresponding tool call ID from the previous assistant message
            if messages and messages[-1].get('role') == 'assistant' and 'tool_calls' in messages[-1]:
                last_tool_calls = messages[-1]['tool_calls']
                if last_tool_calls:
                    tool_call_id = last_tool_calls[-1]['id']  # Use the last one
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": conv['value']
                    })
    
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "tools": tools
    }

def convert_glaive_to_unified(example, index, source_name):
    """Convert Glaive format to unified format"""
    conversation_id = f"{source_name}_{index}"
    
    messages = []
    tool_call_counter = 0
    
    # Parse conversations
    conversations = example['conversations']
    
    # Parse tools (it's a JSON string)
    try:
        tools = json.loads(example['tools'])
    except (json.JSONDecodeError, TypeError):
        tools = []
    
    for conv in conversations:
        if conv['from'] == 'human':
            messages.append({
                "role": "user",
                "content": conv['value']
            })
        elif conv['from'] == 'function_call':
            # Parse function call
            try:
                func_call = json.loads(conv['value'])
                tool_calls = [{
                    "id": f"tool_call_{tool_call_counter}",
                    "name": func_call['name'],
                    "arguments": func_call['arguments']
                }]
                tool_call_counter += 1
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
            except json.JSONDecodeError:
                # If parsing fails, treat as regular message
                messages.append({
                    "role": "assistant",
                    "content": conv['value']
                })
        elif conv['from'] == 'observation':
            # This is tool response
            if messages and messages[-1].get('role') == 'assistant' and 'tool_calls' in messages[-1]:
                last_tool_calls = messages[-1]['tool_calls']
                if last_tool_calls:
                    tool_call_id = last_tool_calls[-1]['id']
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": conv['value']
                    })
        elif conv['from'] == 'gpt':
            messages.append({
                "role": "assistant",
                "content": conv['value']
            })
    
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "tools": tools
    }

def convert_xlam_to_unified(example, index, source_name):
    """Convert XLAM format to unified format"""
    conversation_id = f"{source_name}_{index}"
    
    messages = []
    tool_calls = []
    tool_call_counter = 0
    
    # Add user query
    messages.append({
        "role": "user",
        "content": example['query']
    })
    
    # Parse answers (tool calls) - it's a JSON string
    try:
        answers = json.loads(example['answers'])
        for answer in answers:
            tool_calls.append({
                "id": f"tool_call_{tool_call_counter}",
                "name": answer['name'],
                "arguments": answer['arguments']
            })
            tool_call_counter += 1
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Add assistant message with tool calls
    if tool_calls:
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        })
    
    # Parse tools - it's a JSON string
    try:
        tools = json.loads(example['tools'])
    except (json.JSONDecodeError, TypeError):
        tools = []
    
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "tools": tools
    }

# Dataset configurations
datasets_info = [
    {"id": "Team-ACE/ToolACE", "short_name": "toolace", "converter": convert_toolace_to_unified},
    {"id": "llamafactory/glaive_toolcall_en", "short_name": "glaive", "converter": convert_glaive_to_unified},
    {"id": "Salesforce/xlam-function-calling-60k", "short_name": "xlam", "converter": convert_xlam_to_unified}
]

# Process datasets and create unified format
unified_data = []

for dataset_info in datasets_info:
    print(f"\n=== Processing {dataset_info['id']} ===")
    try:
        dataset = load_dataset(dataset_info['id'])
        split_name = 'train' if 'train' in dataset else list(dataset.keys())[0]
        data = dataset[split_name]
        
        # Take first 500 entries (or all if less than 500)
        num_entries = min(500, len(data))
        print(f"Processing {num_entries} entries from {dataset_info['short_name']}")
        
        for i in range(num_entries):
            try:
                example = data[i]
                converted = dataset_info['converter'](example, i, dataset_info['short_name'])
                unified_data.append(converted)
            except Exception as e:
                print(f"Error converting entry {i} from {dataset_info['short_name']}: {e}")
                continue
        
        print(f"Successfully converted {len([x for x in unified_data if x['conversation_id'].startswith(dataset_info['short_name'])])} entries from {dataset_info['short_name']}")
        
    except Exception as e:
        print(f"Error loading {dataset_info['id']}: {e}")

print(f"\n=== Summary ===")
print(f"Total unified entries: {len(unified_data)}")

# Write to JSONL file
output_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-merge-hf-datasets/workspace/unified_tool_call.jsonl'

with open(output_path, 'w', encoding='utf-8') as f:
    for entry in unified_data:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

print(f"Unified dataset saved to: {output_path}")
print(f"File contains {len(unified_data)} entries")

# Show distribution by source
source_counts = {}
for entry in unified_data:
    source = entry['conversation_id'].split('_')[0]
    source_counts[source] = source_counts.get(source, 0) + 1

print(f"\nDistribution by source:")
for source, count in source_counts.items():
    print(f"  {source}: {count} entries")