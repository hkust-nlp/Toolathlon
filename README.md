<div align="center">

 <p align="center">
    <img src="./assets/toolathlon.svg" alt="Logo" width="500" height="200"/>
</p>

# The Tool Decathlon: Benchmarking Language Agents for <br>Diverse, Realistic, and Long-Horizon Task Execution

[![Website](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://hkust.mintlify.app/)
[![Discord](https://img.shields.io/badge/Join_Our_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/yourcode)
[![arXiv](https://img.shields.io/badge/Paper-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white)](https://arxiv.org/abs/xxxx.xxxxx)
[![Hugging Face](https://img.shields.io/badge/Trajectories-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/hkust-nlp/xxxxxx)


<!-- [Installation](#installation) • [Quick Start](#quick-start) • [Features](#key-features) • [Documentation](./docs/) • [Contributing](./CONTRIBUTING.md) -->

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

### Configuate Global Configs (Part 1: LLM APIs)

Please copy the `configs/global_configs_example.py` to a new file `configs/global_configs.py`:

```
cp configs/global_configs_example.py configs/global_configs.py
```

We use this `configs/global_configs.py` to manage all LLM APIs, you need to open this file and fill in the api keys in it. Note that you do not need to fill in all of them, but instead just fill in the api keys for the providers you want to use. We recommand using [**openrouter**](https://openrouter.ai/), as it enables us to use various LLMs by only configurating one api key.

You can find details about the model providers in `utils/api_model/model_provider.py`.

### Quick Example

After the above two steps, you can directlt run this very quick example. We use *claude-4.5-haiku-1001* via **openrouter** in this example, so make sure you have configurated it.

```
bash scripts/quick_start/quick_start_run.sh
```

You can find the resulted logs, trajectories, and agent workspace all in `dumps_quick_start/claude-4.5-haiku-1001/finalpool/SingleUserTurn-find-alita-paper`.

## Full Preparation

### Configuate Global Configs (Part 2: Containerization)

Make sure you have docker or podman installed and correctly configurated, please fill in your choice in `global_configs.py`

### Configuate App-Aware Tokens, Keys and Credentials

Please copy the `configs/token_key_session_example.py` to a new file `configs/token_key_session.py`:

```
cp configs/token_key_session_example.py configs/token_key_session.py
```

Then please read carefully through `global_preparation/how2register_accounts.md` and follow the guides. You need to register some accounts and configure some tokens/api keys/secrets in `configs/token_key_session.py`. 

### Misc COnfiguration

Simply run the following:
```
bash global_preparation/misc_configuartion.sh
```

### Deployment Needed Apps
```
bash global_preparation/deploy_containers.sh [true|false] # this indicate whether we configure dovecot in poste.io to allow plaintext auth.
```

You can find more details in `deployment/*/scripts/setup.sh` for each local application we deployed.

### Run Single Task

We use the same script to run any task, just simply edit the `task` variable in this script:

```
bash scripts/quick_start/quick_start_run.sh
```

## Evaluate in Parallel with Isolation

为了保证不同任务执行之间的互不干扰，我们实现了在容器里运行执行任务，这同时带来了允许我们并行执行任务的好处，从而极大加速了我们的评估速度。

```
bash scripts/run_parallel.sh
```