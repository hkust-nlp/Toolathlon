<div align="center">

 <p align="center">
    <img src="./assets/toolathlon.svg" alt="Logo" width="500" height="200"/>
</p>

# The Tool Decathlon: Benchmarking Language Agents for <br>Diverse, Realistic, and Long-Horizon Task Execution

[![Website](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://toolathlon.xyz/)
[![Discord](https://img.shields.io/badge/Join_Our_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/8sq8axSR)
[![arXiv](https://img.shields.io/badge/Paper-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white)](https://arxiv.org/abs/2510.25726)
[![Hugging Face](https://img.shields.io/badge/Trajectories-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/hkust-nlp/Toolathlon-Trajectories)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/hkust-nlp/Toolathlon)

</div>

## Introduction
Toolathlon is a benchmark to assess language agents' general tool use in realistic environments. It features 600+ diverse tools based on real-world software environments. Each task requires long-horizon tool calls to complete. Below we show a demo task where the agent needs to automatically check assignments in the email box, and grade them on Canvas.

<div align="center">
  <img src="assets/demo.gif" width="100%" alt="Demo">
</div>

## NOTE
If you are unable/unwilling to install docker/podman, but still want to try our benchmark, please refer to `README_nodocker.md`.

## Quick Start

### Installation Dependencies

#### uv

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
bash global_preparation/install_env_minimal.sh [true|false] # `true` if you have sudo.
```


#### Docker/Podman
For each task we setup a separate container for it to be executed. We assume you have [docker](https://www.docker.com/) or [podman](https://podman.io/) installed and correctly configurated. Please specify your choice on these two in `configs/global_configs.py`.

Then, pull our prepared image:

```
bash global_preparation/pull_toolathlon_image.sh
```

### Configure Global Configs
Simply set these two env variables, note that `TOOLATHLON_OPENAI_BASE_URL` must be an OpenAI SDK compatible one, as our agent scaffold relies on this:

```
export TOOLATHLON_OPENAI_API_KEY="your-custom-api-key"
export TOOLATHLON_OPENAI_BASE_URL="https://your-custom-endpoint.com" # e.g. "https://openrouter.ai/api/v1" for OpenRouter, "https://api.anthropic.com/v1/" for Anthropic
```

This will use our **unified** model provider (more details in `utils/api_model/model_provider.py`). You can also use any model deployed on your own machine, like via [vLLM](https://github.com/vllm-project/vllm) or [SGLang](https://github.com/sgl-project/sglang), in that case you do not need to set the api key.


(Optional) We also provide some pre-configurated options for you in `configs/global_configs.py` to manage all LLM APIs. You may open this file and fill in the api keys in it, and specify which provider you want to use later. 
You can find details about model providers in `utils/api_model/model_provider.py`.

### Quick Example

After the above two steps, we provide a very quick example here. We use *claude-sonnet-4-5* via **openrouter** in this example, so make sure you have configured TOOLATHLON_OPENAI_API_KEY and TOOLATHLON_OPENAI_BASE_URL accordingly if you want to run this script without any modification.

```
bash scripts/run_single_containerized.sh finalpool/find-alita-paper quickstart ./dumps_quick_start/anthropic_claude-sonnet-4-5 anthropic/claude-sonnet-4.5
```

You can find the resulted logs, trajectories, and agent workspace all in `dumps_quick_start/anthropic_claude-sonnet-4-5/finalpool/find-alita-paper`.

## Full Preparation

### Choose a Proper Machine

To run our benchmark, we strongly suggest you deploy it on a Linux machine with docker installed that can directly access the Internet. 
Although you can indeed run our benchmark without sudo, some configurations still need this (you may ask an administrator to help you with this), like configuring *podman* and *inotify* parameters (see "# k8s" part in `global_preparation/install_env_minimal.sh`).
 <!-- or installing dependencies for playwright (see "# install playwright system dependencies" part in `global_preparation/install_env.sh`). -->

### Configure App-Aware Tokens, Keys and Credentials
Please read carefully through [how2register_accounts.md](global_preparation/how2register_accounts.md) and follow the guides. You need to register some accounts and configure some tokens/api keys/secrets in `configs/token_key_session.py`. 

### Misc Configuration

Simply run the following:
```
bash global_preparation/misc_configuartion.sh
```

### Deploy Needed Apps
```
bash global_preparation/deploy_containers.sh [true|false] # this indicate whether we configure dovecot in poste.io to allow plaintext auth.
```

You can find more details in `deployment/*/scripts/setup.sh` for each local application we deployed.

### MCP Servers Verification

Make sure you have finished all the previous steps, and then you can run the following script to check if all MCP servers are working properly, after you setup all the above configs and deployed the app containers:

```
bash global_preparation/check_installation_containerized.sh
```

### Run Single Task

We use the same script `scripts/run_single_containerized.sh` to run any task, just simply switch to another task in the input arguments:

```
bash scripts/run_single_containerized.sh finalpool/{taskname} normal {your_dump_path} {model-name}
```

*Note: There are also other arguments in the script, please take a look at the head of it if for more information. The model name should be exactly the same as the raw name from the provider if you use **unified** model provider, otherwise, please use the alias we preset, see `utils/api_model/model_provider.py` for more details.

## Evaluation in Parallel with Task Isolation

<!-- To ensure that the execution of different tasks does not interfere with each other, we use containerization to run each task in an isolated environment. This also makes it possible to run tasks in parallel, greatly accelerating evaluation speed. -->

<!-- In doing so, we build an image `docker.io/lockon0927/toolathlon-task-image:1016beta`, you can pull it via this: -->

You can run this to enable evaluation in parallel:

```
bash scripts/run_parallel.sh [model-name] {your_dump_path} unified 10
```
*Note: please take a look at the arguments in this script before you run. If you want to use the unified model provider, do remember to export the TOOLATHLON_OPENAI_BASE_URL and TOOLATHLON_OPENAI_API_KEY environment variables.

This will run all the tasks in parallel with at most 10 workers, and you will find all output trajectories and evaluation summary (`eval_stats.json`) in `{your_dump_path}`.

If you'd like to evaluate multiple models in sequence, we provide an ensemble script for you:

```
bash scripts/run_parallel_sequential.sh
```

## Visualization

To facilitate viewing the reasoning trajectories of LLMs, we provide a replay tool for developers to visualize any trajectory in `vis_traj`. After obtaining the results, you can simply run the following command:

```bash
uv run vis_traj/server.py --port 8000 --res_path {your_dump_path}/finalpool/
```

And you can visit localhost:8000 to view trajectories.

## Supporting Multiple Agent Scaffolds  
In addition to the scaffold we have implemented in Toolathlon based on the [openai-agent-sdk](https://github.com/openai/openai-agents-python), we are also committed to introducing more scaffolds for more comprehensive testing. Currently, we have preliminarily integrated [OpenHands](https://github.com/All-Hands-AI/OpenHands), which can be found in our `openhands-compatibility` branch. In the future, we hope to introduce more scaffolds, and we also welcome community contributions of Toolathlon implementations or testing results under other scaffolds.

## Citing Us
If you found our project useful, please cite us as:
```
@article{li2025toolathlon,
      title={The Tool Decathlon: Benchmarking Language Agents for Diverse, Realistic, and Long-Horizon Task Execution}, 
      author={Junlong Li and Wenshuo Zhao and Jian Zhao and Weihao Zeng and Haoze Wu and Xiaochen Wang and Rui Ge and Yuxuan Cao and Yuzhen Huang and Wei Liu and Junteng Liu and Zhaochen Su and Yiyang Guo and Fan Zhou and Lueyang Zhang and Juan Michelini and Xingyao Wang and Xiang Yue and Shuyan Zhou and Graham Neubig and Junxian He},
      year={2025},
      eprint={2510.25726},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2510.25726}, 
}
```

## Contact Information
For help or issues using Toolathlon, you can submit a GitHub issue, send messages in our [discord channel](https://discord.gg/8sq8axSR), or send emails to Junlong Li (jlini@cse.ust.hk) / Junxian He (junxianh@cse.ust.hk).
