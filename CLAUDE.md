# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCPBench-Dev is an evaluation benchmark for Model Context Protocol (MCP) agents. It uses a task-based evaluation framework where AI agents complete various tasks using MCP servers, with both simulated users and direct task execution modes.

## Core Components

### Task Structure
- **Tasks**: Located in `tasks/` directory, organized by category (e.g., `finalpool/`, `jl/`, `debug/`)
- **Task Config**: Each task has a `task_config.json` defining the task parameters
- **Initial Workspace**: Files in `initial_workspace/` that agents can access when starting tasks
- **Evaluation**: Scripts in `evaluation/` directory check task completion
- **Ground Truth**: Expected results stored in `groundtruth_workspace/`

### Key Architecture Files
- `main.py`: Batch task processor for running multiple tasks concurrently
- `demo.py`: Single task runner for development and debugging  
- `utils/task_runner/runner.py`: Core task execution logic with TaskRunner class
- `utils/evaluation/evaluator.py`: Task evaluation framework
- `utils/data_structures/`: Configuration data structures (TaskConfig, AgentConfig, etc.)

### MCP Integration
- MCP server configurations in `configs/mcp_servers/` (YAML files)
- Credentials and tokens in `configs/` directory
- Both npm and Python-based MCP servers supported via UV tools and npm packages

## Common Development Commands

### Environment Setup
```bash
# Install Python dependencies
uv sync

# Install Node.js MCP packages  
npm install

# Install UV tools for MCP servers
uv tool install office-powerpoint-mcp-server
uv tool install office-word-mcp-server
uv tool install git+https://github.com/wandb/wandb-mcp-server
uv tool install cli-mcp-server
uv tool install pdf-tools-mcp@latest
```

### Running Tasks

**Single Task Development/Debug:**
```bash
# Basic debug run
uv run demo.py \
  --eval_config scripts/debug_eval_config.json \
  --task_dir finalpool/find-alita-paper \
  --debug

# With manual user input (real user instead of simulated)
uv run demo.py \
  --eval_config scripts/debug_eval_config.json \
  --task_dir debug/debug-task \
  --debug \
  --manual

# Multi-turn mode
uv run demo.py \
  --eval_config scripts/debug_eval_config.json \
  --task_dir debug/debug-task \
  --debug \
  --multi_turn_mode
```

**Batch Evaluation:**
```bash
uv run main.py \
  --task_dir tasks/finalpool \
  --eval_config scripts/eval_config.json \
  --max_concurrent 10 \
  --output eval_results/run1/results.json
```

### Configuration Files
- `scripts/debug_eval_config.json`: Development configuration
- `scripts/eval_config.json`: Production evaluation configuration  
- Model-specific configs in `scripts/model_wise/` (e.g., `eval_claude-4-sonnet.json`, `eval_gpt-4.1-mini.json`)

## Development Workflow

### Adding New Tasks
1. Create task directory under `tasks/[category]/[task-name]/`
2. Add `task_config.json` with task parameters
3. Create `initial_workspace/` with starting files
4. Add evaluation script in `evaluation/main.py`
5. Create `groundtruth_workspace/` with expected results
6. Add task documentation in `docs/` directory (agent_system_prompt.md, task.md, user_system_prompt.md)
7. For Chinese tasks, add `_cn` suffixed versions of prompts and workspaces

### Key Command Parameters
- `--debug`: Enable verbose logging and detailed output
- `--manual`: Use real user input instead of simulated user
- `--multi_turn_mode`: Enable multi-turn conversations vs single-turn mode
- `--allow_resume`: Resume from previous execution state
- `--with_proxy`: Enable proxy for network requests
- `--eval_config`: Path to evaluation configuration JSON file
- `--task_dir`: Relative path from `tasks/` directory to specific task

### File Locations
- Task configurations: `tasks/[category]/[task-name]/task_config.json`
- MCP server configs: `configs/mcp_servers/*.yaml`
- Evaluation results: Saved to `recorded_trajectories_v2/` or specified output path
- Logs: `log.json` files in task result directories
- Credentials: `configs/global_configs.py` (from `global_configs_example.py` template)

## Architecture Notes

### Core Framework
- Uses OpenAI Agents framework with custom MCP patches in `utils/openai_agents_monkey_patch/`
- Task execution managed by `TaskRunner` class in `utils/task_runner/runner.py`
- System prompts support template variables like `!!<<<<||||workspace_dir||||>>>>!!`
- Both English and Chinese task modes supported via `cn_mode` parameter

### Execution Flow
- Tasks configured via dataclasses in `utils/data_structures/`
- Agent and user models configured separately with different temperature settings
- Concurrent execution managed via asyncio semaphores
- Cost tracking for both agent and user LLM calls
- Resume capability for long-running tasks with state preservation

### Evaluation System
- Two-stage evaluation: local file state checking + dialogue history analysis
- Ground truth comparison against expected results
- Automated evaluation scripts per task in `evaluation/main.py`
- 以瞎猜接口为耻,以认真查询为荣。
以模糊执行为耻,以寻求确认为荣。
以臆想业务为耻,以人类确认为荣。
以创造接口为耻,以复用现有为荣。
以跳过验证为耻,以主动测试为荣。
以破坏架构为耻,以遵循规范为荣。
以假装理解为耻,以诚实无知为荣。
以盲目修改为耻,以谨慎重构为荣