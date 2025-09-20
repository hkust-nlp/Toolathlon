#!/bin/bash

# pip install gradio
# pip install httpx==0.23.0
# Initialize variables
data_dir=TO_BE_FILLED
run_names=""
temperature=0.0
# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --data_dir)
            data_dir="$2"
            shift 2
            ;;
        --run_names)
            run_names="$2"
            shift 2
            ;;
        --temperature)
            temperature="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --data_dir <dir> --run_names <name1,name2,name3,...>"
            exit 1
            ;;
    esac
done

# Check if required parameters are provided
if [ -z "$data_dir" ] || [ -z "$run_names" ]; then
    echo "Both --data_dir and --run_names are required"
    echo "Usage: $0 --data_dir <dir> --run_names <name1,name2,name3,...>"
    exit 1
fi

# Split run_names by comma and launch visualizer for each
IFS=',' read -ra NAMES <<< "$run_names"
for run_name in "${NAMES[@]}"; do
    echo "Starting visualizer for:"
    echo "  Data directory: $data_dir"
    echo "  Run name: $run_name"
    echo "  Temperature: $temperature"
    python examples/simplelr_math_eval/visualizer.py --data_dir "$data_dir" --run_name "$run_name" --temperature "$temperature" &
    sleep 5
done