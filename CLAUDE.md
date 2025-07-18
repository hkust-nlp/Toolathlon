# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCPBench-Dev is an evaluation benchmark for Model Context Protocol (MCP) agents. It uses a task-based evaluation framework where AI agents complete various tasks using MCP servers, with both simulated users and direct task execution modes.

## Core Components

### Task Structure
- **Tasks**: Located in `tasks/` directory, organized by category (e.g., `finalpoolcn/`, `jl/`, `debug/`)
- **Task Config**: Each task has a `task_config.json` defining the task parameters
- **Initial Workspace**: Files in `initial_workspace/` that agents can access when starting tasks
- **Evaluation**: Scripts in `evaluation/` directory check task completion
- **Ground Truth**: Expected results stored in `groundtruth_workspace/`

### Key Architecture Files
- `main.py`: Batch task processor for running multiple tasks concurrently
- `demo.py`: Single task runner for development and debugging  
- `utils/task_runner/runner.py`: Core task execution logic
- `utils/evaluation/evaluator.py`: Task evaluation framework
- `utils/data_structures/`: Configuration data structures (TaskConfig, AgentConfig, etc.)

### MCP Integration
- MCP server configurations in `configs/mcp_servers/` (YAML files)
- Credentials and tokens in `configs/` directory
- Both npm and Python-based MCP servers supported

## Common Development Commands

### Environment Setup
```bash
# Install Python dependencies
uv sync

# Install Node.js MCP packages  
npm install

# Install UV tools
uv tool install office-powerpoint-mcp-server
uv tool install office-word-mcp-server
uv tool install git+https://github.com/wandb/wandb-mcp-server
uv tool install cli-mcp-server
uv tool install pdf-tools-mcp@latest
```

### Running Tasks

**Single Task Development/Debug:**
```bash
uv run demo.py \
  --eval_config scripts/debug_eval_config.json \
  --task_dir finalpoolcn/find-alita-paper \
  --debug
```

**Batch Evaluation:**
```bash
uv run main.py \
  --task_dir tasks/finalpoolcn \
  --eval_config scripts/eval_config.json \
  --max_concurrent 10 \
  --output eval_results/run1/results.json
```

### Configuration Files
- `scripts/debug_eval_config.json`: Development configuration
- `scripts/eval_config.json`: Production evaluation configuration  
- Model-specific configs in `scripts/model_wise/`

## Development Workflow

### Adding New Tasks
1. Create task directory under `tasks/[category]/[task-name]/`
2. Add `task_config.json` with task parameters
3. Create `initial_workspace/` with starting files
4. Add evaluation script in `evaluation/main.py`
5. Create `groundtruth_workspace/` with expected results
6. Add task documentation in `docs/` directory

### Key Parameters
- `--debug`: Enable verbose logging
- `--manual`: Use real user input instead of simulated user
- `--multi_turn_mode`: Enable multi-turn conversations vs single-turn  
- `--allow_resume`: Resume from previous execution state
- `--with_proxy`: Enable proxy for network requests

### File Locations
- Task configurations: `tasks/[category]/[task-name]/task_config.json`
- MCP server configs: `configs/mcp_servers/*.yaml`
- Evaluation results: Saved to `recorded_trajectories_v2/` or specified output path
- Logs: `log.json` files in task result directories

## Architecture Notes

- Uses OpenAI Agents framework with custom MCP patches in `utils/openai_agents_monkey_patch/`
- Supports both English and Chinese task modes
- Concurrent execution managed via asyncio semaphores
- Cost tracking for both agent and user LLM calls
- Resume capability for long-running tasks