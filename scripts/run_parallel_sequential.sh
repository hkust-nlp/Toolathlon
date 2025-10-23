# Some Configurations
TASK_IMAGE=lockon0927/toolathlon-task-image:1016beta # this is the image we use for parallel evaluation
TASK_LIST_FILE="" # you can specify a file with each line representing a task, by doing so you can evaluate on an arbitrary subset of tasks
DUMP_PATH="./dumps_finalexp_openhands" # you must have this ./ prefix
poste_configure_dovecot=true # or `false` if your Linux distribution does not need to configure Dovecot to allow plaintext auth
WROKERS=10

WROKERS=10

MODEL_PROVIDER_LIST=(
    "claude-4.5-haiku-1001|openrouter"
)

# Main Loop
for attempt in {1..1}; do
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # Parse model name and provider
        MODEL_SHORT_NAME="${model_provider%%|*}"  # Extract left part up to first |
        PROVIDER="${model_provider##*|}"         # Extract right part after last |
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh $poste_configure_dovecot
        bash scripts/run_parallel.sh "$MODEL_SHORT_NAME" "$DUMP_PATH/${MODEL_SHORT_NAME}_${attempt}" "$PROVIDER" "$TASK_LIST_FILE" "$WROKERS" "$TASK_IMAGE"
    done
done
