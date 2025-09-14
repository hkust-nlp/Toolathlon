# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LUFFY (Learning to Reason Under Off-Policy Guidance) is a reinforcement learning framework for mathematical reasoning in large language models. It bridges zero-RL and imitation learning by incorporating off-policy reasoning traces during training, built on top of the GRPO framework with veRL as the underlying infrastructure.

## Development Environment Setup

```bash
# Create and activate conda environment
conda create -n luffy python=3.10
conda activate luffy

# Install dependencies
cd luffy
pip install -r requirements.txt
pip install -e .
cd verl
pip install -e .
```

**Flash Attention Installation**: If flash-attn installation fails, manually install from releases:
```bash
wget https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.3/flash_attn-2.7.3+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
pip install flash_attn-2.7.3+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
```

## Common Commands

### Data Preparation
```bash
# Convert training data to parquet format
cd data
python prepare_train.py

# Prepare SFT data (for baseline comparisons)
python prepare_sft.py

# Prepare SFT+RL data
python prepare_train_sft_rl.py
```

### Training
```bash
# Main LUFFY training
cd exp_scripts
bash train.sh

# RL with SFT Loss training
bash train_rl_sft_loss.sh

# SFT+RL training (two-stage)
bash train_sft_rl.sh

# On-policy RL baseline
bash train_on_policy.sh
```

### Evaluation
```bash
# Run evaluation on math benchmarks
ROOT=YOUR_ROOT_PATH
DATA=$ROOT/data/valid.all.parquet
OUTPUT_DIR=./results/
MODEL_PATH=Elliott/LUFFY-Qwen-Math-7B-Zero
MODEL_NAME=luffy

CUDA_VISIBLE_DEVICES=0,1,2,3 python eval_scripts/generate_vllm.py \
  --model_path $MODEL_PATH \
  --input_file $DATA \
  --remove_system True \
  --add_oat_evaluate True \
  --output_file $OUTPUT_DIR/$MODEL_NAME.jsonl \
  --template own > $OUTPUT_DIR/$MODEL_NAME.log
```

### Testing
```bash
# Run unit tests (located in luffy/verl/tests/)
cd luffy/verl
python -m pytest tests/
```

## Architecture Overview

### Core Components

**Main Framework (`luffy/verl/verl/`)**:
- `mix_src/`: LUFFY-specific implementations
  - `main_mix_ppo.py`: Main training entry point
  - `mix_actor.py`: Actor with off-policy guidance
  - `mix_core_alg.py`: Core LUFFY algorithm
  - `mix_trainer.py`: Training orchestration
  - `math_verify_reward.py`: Mathematical reward functions

**Training Pipeline**:
1. **Data Loading**: Parquet files with on-policy/off-policy traces
2. **Model Components**: Actor, Critic, Reference model, Reward model
3. **Training**: GRPO with off-policy guidance and policy shaping
4. **Evaluation**: Mathematical reasoning verification

**Key Algorithm Features**:
- **Off-Policy Integration**: Importance sampling with regularization
- **Policy Shaping**: Emphasizes low-probability crucial actions
- **Advantage Estimation**: Combines on-policy rollouts with off-policy demonstrations

### Technical Stack

**Core Dependencies**:
- `torch==2.4.0`: Deep learning framework
- `transformers==4.46.3`: Model architectures (version locked)
- `vllm==0.6.3`: Fast inference engine
- `deepspeed==0.15.0`: Distributed training
- `flash_attn==2.7.3`: Memory-efficient attention
- `math-verify==0.6.0`: Mathematical evaluation
- `ray==2.12.0`: Distributed computing

**Model Support**: Qwen2.5-Math series, DeepSeek models, general instruction models

**Hardware Requirements**: 
- Default: 8 GPUs (A100-80GB optimized)
- Memory: Optimized for large model training with gradient checkpointing

## Key File Locations

**Training Scripts**: `exp_scripts/train*.sh`
**Core Algorithm**: `luffy/verl/verl/mix_src/`
**Data Processing**: `data/prepare_*.py`
**Evaluation**: `eval_scripts/generate_vllm.py`
**Configuration**: Training parameters embedded in shell scripts
**Models**: Hugging Face collection at `Elliott/luffy-rl-*`

## Development Patterns

**Configuration Management**: Training parameters are primarily configured through shell scripts in `exp_scripts/` rather than separate config files.

**Data Format**: Uses parquet files for efficient data loading with on-policy and off-policy reasoning traces.

**Distributed Training**: Built on Ray with DeepSpeed integration for multi-GPU scaling.

**Evaluation Pipeline**: Automated evaluation on 6 math benchmarks (AIME, AMC, MATH-500, etc.) and 3 out-of-distribution tasks.

**Model Checkpointing**: Supports both native PyTorch and HuggingFace checkpoint formats.

## Debugging and Monitoring

**Logging**: Training progress logged to wandb (configure WANDB_KEY in scripts)
**Evaluation Metrics**: Mathematical accuracy with math-verify grader
**Performance Monitoring**: GPU memory usage optimized with flash attention and gradient checkpointing
**Error Handling**: Mathematical verification includes sympy-based symbolic evaluation

## Important Notes

- **Version Constraints**: transformers version is locked to 4.46.3 for compatibility
- **CUDA Requirements**: Requires NVIDIA GPUs with CUDA support for training
- **Memory Management**: Uses gradient checkpointing and mixed precision (bf16) for efficiency
- **Evaluation**: Uses specialized prompts for different model types (PRIME, SimpleRL, etc.)
- **Data Privacy**: No sensitive credential handling; uses public datasets and models