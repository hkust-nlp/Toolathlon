import subprocess
import os
import sys

workspace_dir = "/ssddata/mcpbench/zhaojian/mcpbench_dev/recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpool/SingleUserTurn-huggingface-upload/workspace"
os.chdir(workspace_dir)

# Add utils to path to import benchmark utils
sys.path.insert(0, os.path.join(workspace_dir, 'evaluation'))
from utils.benchmark_utils import BENCHMARK_CALCULATORS

# List of all benchmark categories
BENCHMARK_CATEGORIES = list(BENCHMARK_CALCULATORS.keys())

def run_benchmark_evaluation(benchmark_name, model_path):
    """Run evaluation for a specific benchmark category"""
    benchmark_script = os.path.join("evaluation", "benchmarks", benchmark_name, "eval.py")
    
    if not os.path.exists(benchmark_script):
        print(f"Warning: Benchmark script not found: {benchmark_script}")
        return None
    
    try:
        result = subprocess.run(
            [sys.executable, benchmark_script, model_path],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=60
        )
        score = float(result.stdout.strip())
        return score
    except subprocess.CalledProcessError as e:
        print(f"Error running {benchmark_name} evaluation: {e.stderr}")
        return None
    except (ValueError, TypeError):
        print(f"Warning: Could not parse score from {benchmark_name}")
        return None
    except subprocess.TimeoutExpired:
        print(f"Timeout running {benchmark_name} evaluation")
        return None

# Get detailed results for the best checkpoint (step_1000)
best_checkpoint_path = os.path.join(workspace_dir, "checkpoints", "step_1000")
print(f"Getting detailed results for best checkpoint: {best_checkpoint_path}")
print("="*60)

benchmark_scores = {}

# Run evaluation for each benchmark category
for benchmark in BENCHMARK_CATEGORIES:
    print(f"Running {benchmark}...")
    score = run_benchmark_evaluation(benchmark, best_checkpoint_path)
    benchmark_scores[benchmark] = score
    if score is not None:
        print(f"  {benchmark}: {score:.3f}")
    else:
        print(f"  {benchmark}: FAILED")

print("\n" + "="*60)
print("DETAILED BENCHMARK RESULTS FOR STEP_1000:")
print("="*60)
for benchmark, score in benchmark_scores.items():
    if score is not None:
        print(f"{benchmark}: {score:.3f}")
    else:
        print(f"{benchmark}: FAILED")