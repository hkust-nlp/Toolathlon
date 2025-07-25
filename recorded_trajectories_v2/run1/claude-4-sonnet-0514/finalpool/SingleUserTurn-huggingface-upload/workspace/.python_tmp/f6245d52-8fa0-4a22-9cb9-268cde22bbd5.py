import subprocess
import os
import sys

# Change to the workspace directory
workspace_dir = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-huggingface-upload/workspace"
os.chdir(workspace_dir)

# Get all checkpoint directories
checkpoints_dir = os.path.join(workspace_dir, "checkpoints")
checkpoint_dirs = [d for d in os.listdir(checkpoints_dir) if os.path.isdir(os.path.join(checkpoints_dir, d))]
checkpoint_dirs.sort(key=lambda x: int(x.split('_')[1]))  # Sort by step number

print("Found checkpoints:", checkpoint_dirs)

# Evaluate each checkpoint
checkpoint_scores = {}
for checkpoint in checkpoint_dirs:
    checkpoint_path = os.path.join(checkpoints_dir, checkpoint)
    print(f"\nEvaluating {checkpoint}...")
    
    try:
        result = subprocess.run(
            [sys.executable, "evaluation/eval.py", checkpoint_path],
            capture_output=True,
            text=True,
            cwd=workspace_dir,
            timeout=300  # 5 minute timeout per evaluation
        )
        
        if result.returncode == 0:
            score = float(result.stdout.strip())
            checkpoint_scores[checkpoint] = score
            print(f"{checkpoint}: {score}")
        else:
            print(f"Error evaluating {checkpoint}: {result.stderr}")
            checkpoint_scores[checkpoint] = None
            
    except subprocess.TimeoutExpired:
        print(f"Timeout evaluating {checkpoint}")
        checkpoint_scores[checkpoint] = None
    except Exception as e:
        print(f"Exception evaluating {checkpoint}: {e}")
        checkpoint_scores[checkpoint] = None

print("\n" + "="*50)
print("EVALUATION RESULTS:")
print("="*50)
for checkpoint, score in checkpoint_scores.items():
    if score is not None:
        print(f"{checkpoint}: {score:.3f}")
    else:
        print(f"{checkpoint}: FAILED")

# Find the best checkpoint
valid_scores = {k: v for k, v in checkpoint_scores.items() if v is not None}
if valid_scores:
    best_checkpoint = max(valid_scores.keys(), key=lambda k: valid_scores[k])
    best_score = valid_scores[best_checkpoint]
    print(f"\nBEST CHECKPOINT: {best_checkpoint} with score {best_score:.3f}")
else:
    print("\nNo valid scores found!")