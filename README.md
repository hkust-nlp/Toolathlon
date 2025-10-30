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

## OpenHands-Compatible Branch

### Installation

This branch is primarily intended for evaluating **Toolathlon** using the **OpenHands** scaffold.

You can configure the environment using the same script as in the main branch:

```bash
bash global_preparation/install_env.sh [true|false]  # Use `true` if you have sudo privileges
```

Next, deploy the required applications:

```bash
bash global_preparation/deploy_containers.sh [true|false]  # Set to `true` to configure Dovecot in Poste.io to allow plaintext authentication
```

### Configuration

We assume that you have already completed the configuration steps from the main branch **on the same machine**.

Then, simply copy the following files into the `configs` directory from the main branch:

```
configs/gcp-oauth.keys.json  
configs/gcp-service_account.keys.json  
configs/global_configs.py  
configs/google_credentials.json  
configs/token_key_session.py
```

### Running

To execute a single task, use the same script as in the main branch and set the `task` variable to the task you want to evaluate:

```bash
bash scripts/quick_start/quick_start_run.sh
```

The outputs from the tasks will be stored in:

```
./dumps_quick_start
```

> **Note:** We have not yet extensively tested the OpenHands scaffold across all combinations of tasks and models, so there may still be compatibility issues. Please keep this in mind.
