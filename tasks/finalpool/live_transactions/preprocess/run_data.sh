# python construct_data.py \
#     --scale 1000 \
#     --suspicious-count 10 \
#     --export-csv \
#     --output-dir /Users/zengweihao/mcp-bench/mcpbench_dev/tasks/weihao/live_transactions/preprocess/big_csv


python query_suspicious_transaction.py \
    --transaction-id T8492XJ3 \
    --csv-dir /Users/zengweihao/mcp-bench/mcpbench_dev/tasks/weihao/live_transactions/preprocess/big_csv \
    --output /Users/zengweihao/mcp-bench/mcpbench_dev/tasks/weihao/live_transactions/preprocess/big_csv/T8492XJ3_investigation_report.json \
    --show-summary