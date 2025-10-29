<div align="center">

 <p align="center">
    <img src="./assets/toolathlon.svg" alt="Logo" width="500" height="200"/>
</p>

# The Tool Decathlon: Benchmarking Language Agents for <br>Diverse, Realistic, and Long-Horizon Task Execution

[![Website](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://toolathlon.xyz/)
[![Discord](https://img.shields.io/badge/Join_Our_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/8sq8axSR)
[![arXiv](https://img.shields.io/badge/Paper-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white)](https://arxiv.org/abs/xxxx.xxxxx)
[![Hugging Face](https://img.shields.io/badge/Trajectories-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/hkust-nlp/Toolathlon-Trajectories)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/hkust-nlp/Toolathlon)

</div>

## Introduction
Toolathlon is a benchmark to assess language agents' general tool use in realistic environments. It features 600+ diverse tools based on real-world software environments. Each task requires long-horizon tool calls to complete. Below we show a demo task where the agent needs to automatically check assignments in the email box, and grade them on Canvas.

<div align="center">
  <img src="assets/demo.gif" width="100%" alt="Demo">
</div>


## Quick Start

### Installation Dependencies

Make sure you have `uv` installed, otherwise please install it:

```
# this is for macOS and linux command
# by default it will install uv to $HOME/.local/bin
# you probably need to add it to your $PATH
curl -LsSf https://astral.sh/uv/install.sh | sh

# check whether uv can be found
which uv
```

We provide one command to install everything, we maintain the environment with `uv`. Just run:


```
bash global_preparation/install_env.sh [true|false] # `true` if you have sudo.
```

### Configure Global Configs (Part 1: LLM APIs)

Please copy the `configs/global_configs_example.py` to a new file `configs/global_configs.py`:

```
cp configs/global_configs_example.py configs/global_configs.py
```

Then simply set these two envariables, note that `TOOLATHLON_OPENAI_BASE_URL` must be an OpenAI SDK compatible one, as our agent scaffold relies this:

```
export TOOLATHLON_OPENAI_API_KEY="your-custom-api-key"
export TOOLATHLON_OPENAI_BASE_URL="https://your-custom-endpoint.com" # e.g. "https://api.anthropic.com/v1/" for Anthropic, "https://openrouter.ai/api/v1" for OpenRouter
```

This will use our unified model provider. You can also use any model deployed on your own machine, like via [vLLM](https://github.com/vllm-project/vllm) or [SGLang](https://github.com/sgl-project/sglang), in that case you do not need to set the api key.


We also provide some pre configurated options for you in `configs/global_configs.py` to manage all LLM APIs. You need to open this file and fill in the api keys in it. Note that you do not need to fill in all of them, but instead just fill in the api keys for the providers you want to use. We recommend using [**openrouter**](https://openrouter.ai/), as it enables us to use various LLMs by only configurating one api key.


You can find details about model providers in `utils/api_model/model_provider.py`.

### Quick Example

After the above two steps, you can directly run this very quick example, this will call claude-sonnet-4-5 to execute the task.
<!-- We use *claude-4.5-haiku-1001* via **openrouter** in this example, so make sure you have configured it. -->

```
bash scripts/quick_start/quick_start_run.sh
```

You can find the resulted logs, trajectories, and agent workspace all in `dumps_quick_start/claude-sonnet-4-5/finalpool/SingleUserTurn-find-alita-paper`.

## Full Preparation

### Choose a Proper Machine

To run our benchmark, we strongly suggest you deploy it on a ***Linux*** machine with ***docker*** installed that can directly access the Internet. 
Although you can indeed run our benchmark without sudo, some configurations still need this (you may ask an administrator to help you with this), like configuring *podman* and *inotify* parameters (see "# k8s" part in `global_preparation/install_env.sh`) or installing dependencies for playwright (see "# install playwright system dependencies" part in `global_preparation/install_env.sh`).


### Configure Global Configs (Part 2: Containerization)

Make sure you have docker or podman installed and correctly configured, please fill in your choice in `global_configs.py`

### Configure App-Aware Tokens, Keys and Credentials

Please copy the `configs/token_key_session_example.py` to a new file `configs/token_key_session.py`:

```
cp configs/token_key_session_example.py configs/token_key_session.py
```

Then please read carefully through `global_preparation/how2register_accounts.md` and follow the guides. You need to register some accounts and configure some tokens/api keys/secrets in `configs/token_key_session.py`. 

### Misc Configuration

Simply run the following:
```
bash global_preparation/misc_configuartion.sh
```

### Deployment Needed Apps
```
bash global_preparation/deploy_containers.sh [true|false] # this indicate whether we configure dovecot in poste.io to allow plaintext auth.
```

You can find more details in `deployment/*/scripts/setup.sh` for each local application we deployed.

### MCP Servers Verification

You can simply run this script to check if all MCP servers are working properly, after you setup all the above configs and deployed the app containers:

```
uv run -m global_preparation.check_installation
```

### Run Single Task

We use the same script `scripts/quick_start/quick_start_run.sh` to run any task, just simply edit the `task` variable in this script:

```
bash scripts/quick_start/quick_start_run.sh
```

## Evaluation in Parallel with Task Isolation

To ensure that the execution of different tasks does not interfere with each other, we use containerization to run each task in an isolated environment. This also makes it possible to run tasks in parallel, greatly accelerating evaluation speed.

In doing so, we build an image `docker.io/lockon0927/toolathlon-task-image:1016beta`, you can pull it via this:

```
bash global_preparation/pull_image_for_parallelism.sh
```

Then you can run this:

```
bash scripts/run_parallel.sh gpt-5-mini ./{your_dump_path} openrouter "" 10
```
*Note: please take a look at the arguments in this script before you run. If you want to use the unified model provider, do remember to export the TOOLATHLON_OPENAI_BASE_URL and TOOLATHLON_OPENAI_API_KEY environment variables.

This will run all the tasks in parallel with at most 10 workers, and you will find all output trajectories and evaluation summary (`eval_stats.json`) in `./{your_dump_path}`.

If you'd like to evaluate multiple models in sequence, we provide an ensemble script for you:

```
bash scripts/run_parallel_sequential.sh
```

## Visualization
To facilitate viewing the reasoning trajectories of LLMs, we provide a replay tool for developers to visualize any trajectory in `vis_traj`.
### Prepare Trajectory
After obtaining the results for a task, you need to perform a data format conversion first. Taking the `notion-hr` task as an example, you can run the following command:

```bash
uv run vis_traj/convert_format.py \
--input_path /path/to/your/results/notion-hr/ \
--output_file yourmodel_notion-hr.json
```

The directory `/path/to/your/results/notion-hr/` should contain: `traj_log.json` and `eval_res.json`.

You can do this multiple times to convert as many trajectories as you want to visualize them later.

### Start Replay Server
Then, simply run the following command:

```bash
uv run vis_traj/server.py --port 8000
```

And you can visit localhost:8000 to view all trajectories you have converted.

## Supporting Multiple Agent Scaffolds  
In addition to the scaffold we have implemented in Toolathlon based on the [openai-agent-sdk](https://github.com/openai/openai-agents-python), we are also committed to introducing more scaffolds for more comprehensive testing. Currently, we have preliminarily integrated [OpenHands](https://github.com/All-Hands-AI/OpenHands), which can be found in our `openhands-compatibility` branch. In the future, we hope to introduce more scaffolds, and we also welcome community contributions of Toolathlon implementations or testing results under other scaffolds.

## Citing Us
If you found our project useful, please cite us as:
```
TBD
```

## Contact Information
For help or issues using Toolathlon, you can submit a GitHub issue, send messages in our [discord channel](https://discord.gg/8sq8axSR), or send emails to Junlong Li (jlini@cse.ust.hk) / Junxian He (junxianh@cse.ust.hk).