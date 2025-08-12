import json

# Show one complete example from each source
output_path = '/ssddata/mcpbench/wenshuo/eval/final_new/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-merge-hf-datasets/workspace/unified_tool_call.jsonl'

examples_shown = {"toolace": 0, "glaive": 0, "xlam": 0}

with open(output_path, 'r', encoding='utf-8') as f:
    for line in f:
        entry = json.loads(line.strip())
        source = entry['conversation_id'].split('_')[0]
        
        if examples_shown[source] == 0:
            print(f"\n{'='*60}")
            print(f"COMPLETE EXAMPLE FROM {source.upper()}")
            print(f"{'='*60}")
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            examples_shown[source] = 1
            
        if all(count > 0 for count in examples_shown.values()):
            break