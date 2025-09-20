set -ex
# export CUDA_VISIBLE_DEVICES=7
PROMPT_TYPE=$1
MODEL_NAME_OR_PATH=$2
OUTPUT_DIR=$3
temperature=$4
max_tokens=$5
top_p=$6
benchmarks=${7:-"gsm8k,math500,minerva_math,gaokao2023en,olympiadbench,college_math,aime24,amc23"}
SPLIT="test"
NUM_TEST_SAMPLE=-1
OVERWRITE=${8:-false}
N_SAMPLING=${9:-1}
# English open datasets
DATA_NAME=${benchmarks}

if [ "$OVERWRITE" = "true" ]; then
    OVERWRITE="--overwrite"
else
    OVERWRITE=""
fi
# Split benchmarks into two groups
IFS=',' read -ra BENCHMARK_ARRAY <<< "$benchmarks"
REGULAR_BENCHMARKS=()
SPECIAL_BENCHMARKS=()

for benchmark in "${BENCHMARK_ARRAY[@]}"; do
    if [[ "$benchmark" == "aime24" || "$benchmark" == "amc23" ]]; then
        SPECIAL_BENCHMARKS+=("$benchmark")
    else
        REGULAR_BENCHMARKS+=("$benchmark")
    fi
done


# If temperature is 0, combine the benchmark arrays
if [ "$temperature" = "0.0" ] || [ "$temperature" = "0" ]; then
    REGULAR_BENCHMARKS=("${REGULAR_BENCHMARKS[@]}" "${SPECIAL_BENCHMARKS[@]}")
    SPECIAL_BENCHMARKS=()
fi

# Run regular benchmarks with n_sampling=1
if [ ${#REGULAR_BENCHMARKS[@]} -gt 0 ]; then
    REGULAR_BENCHMARKS_STR=$(IFS=,; echo "${REGULAR_BENCHMARKS[*]}")
    TOKENIZERS_PARALLELISM=false \
    python -u math_eval.py \
        --model_name_or_path ${MODEL_NAME_OR_PATH} \
        --data_name ${REGULAR_BENCHMARKS_STR} \
        --output_dir ${OUTPUT_DIR} \
        --split ${SPLIT} \
        --prompt_type ${PROMPT_TYPE} \
        --num_test_sample ${NUM_TEST_SAMPLE} \
        --max_tokens_per_call ${max_tokens} \
        --seed 0 \
        --temperature ${temperature} \
        --n_sampling ${N_SAMPLING} \
        --top_p ${top_p} \
        --start 0 \
        --end -1 \
        --use_vllm \
        --save_outputs \
        ${OVERWRITE}
fi

# Run special benchmarks (aime24, amc23) with n_sampling=8
if [ ${#SPECIAL_BENCHMARKS[@]} -gt 0 ]; then
    SPECIAL_BENCHMARKS_STR=$(IFS=,; echo "${SPECIAL_BENCHMARKS[*]}")
    TOKENIZERS_PARALLELISM=false \
    python -u math_eval.py \
        --model_name_or_path ${MODEL_NAME_OR_PATH} \
        --data_name ${SPECIAL_BENCHMARKS_STR} \
        --output_dir ${OUTPUT_DIR} \
        --split ${SPLIT} \
        --prompt_type ${PROMPT_TYPE} \
        --num_test_sample ${NUM_TEST_SAMPLE} \
        --max_tokens_per_call ${max_tokens} \
        --seed 0 \
        --temperature ${temperature} \
        --n_sampling ${N_SAMPLING} \
        --top_p ${top_p} \
        --start 0 \
        --end -1 \
        --use_vllm \
        --save_outputs \
        ${OVERWRITE}
fi
