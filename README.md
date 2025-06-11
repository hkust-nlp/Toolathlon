# MCPBench-Dev

Project Page: https://www.notion.so/hkust-nlp/Meeting-Notes-1f939bdc1c6b80fbbc7fe5ea22c2d038

----
#### NOTE: this readme is still under construction, please do not hesitiate to ping me (junlong) at any time. You are always welcomed!
----
### Quick Start

#### Use a Saperate Branch
Please set a saperate branch for yourselves in for development. Do not push to master directly without notification, thanks!

#### About Proxy
Please see `FAQs/setup_proxy.md` to see how to set up a proxy for your terminal/cmd. I only provide some general guides, so you may need extra effort to solve the proxy issue, e.g. via Google Search and asking LLMs.

You may need to configure some proxies for your MCP servers, e.g. `configs/mcp_servers/playwright.yaml`. You just need to uncomment the corresponding lines, the code will automatically load proxy from `configs/global_configs.py`

#### Basic Env Setup
0. install uv

    please refer to the official [website](https://github.com/astral-sh/uv), you may need to switch on some proxies in this process

    you should be able to see some guide after `uv`

1. install this project
    ```
    git clone https://github.com/hkust-nlp/mcpbench_dev.git
    uv init mcpbench_dev --python=3.12
    cd mcpbench_dev
    ```

2. set up pypi mirror (optional)
    for chinese users who do not want to switch on proxy, you can add the following lines to `pyproject.toml`

    ```
    [[tool.uv.index]]
    url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
    default = true
    ```

    to use Tsinghua Pypi mirror

3. install basic dependencies
    ```
    uv add -r requirements.txt
    ```

#### Install Needed MCPs

1. install npm (see `FAQs/npm_install.md`)

2. install local npm packages
    ```
    npm install
    ```
    it will automatically check the `package.json` and `package-lock.json`
    you may encounter some proxy issue, see `FAQs/npx_install.md`.

3. install local uv tools

    some mcp servers are launched via `uvx`, so we install them in advance to avoid installing them every time
    ```
    uv tool install office-powerpoint-mcp-server
    uv tool install office-word-mcp-server
    ```

    they will be by default installed under ~/.local/share/uv/tools
    
    you can also assign another install dir via `UV_TOOL_DIR` envoronment var

#### Demo
1. Set up global configs
    please fill in the blanks in `configs/global_configs_example.py` and copy the filled one as `configs/global_configs.py`.
2. Try `uv run demo.py` (suppose you are using aihubmix)
    ```
    uv run demo.py \
    --eval_config scripts/eval_config.json \
    --task_config tasks/dev/filesystem_001.json \
    --debug
    ```

#### Eval
In real evaluation setting, we now use the `task_dir` to specify the subset we want to evaluate a model, the following command take the `dev` subset as an example.

1. Try this

    ```
    uv run main.py \
    --task_dir tasks/dev \
    --eval_config scripts/eval_config.json \
    --max_concurrent 10 \
    --output eval_results/dev/batch_results.json
    ```

### Overview of Framework

#### TLDR
To add a task, you need to set 
- a new task config
e.g. `tasks/dev/filesystem_001.json`

- corresponding initial states and pre-process script
e.g. `initial_states/dev/filesystem_001`

- groundtruth local states and evaluation script
e.g. `groundtruth/dev/filesystem_001`

Also, set the global evaluation config, see `scripts/eval_config.json`, which specify some global parameters for this benchmark.

Then you can `uv run demo.py` (with some correct arguments) as a test for your newly added task.

#### Details
> Task

`Task` is the basic element of one test sample. Each `Task` is represented by a task config, see `utils/data_structures/task_config.py` for details.

In general, task configs are stored as json files, like `tasks/dev/filesystem_001.json`. It will be read and loaded as `TaskConfig` in `utils/data_structures/task_config.py` for later use.

The main components of a `TaskConfig` are the followings:

> Initialization

We first need to prepare the initial state of a `Task`. In current simple cases, it means that we need to copy some preloaded files into a specific `agent_workspace` path, so that the agent can see and operate these files when solving the tasks.

An example is under `initial_states/dev/filesystem_001`. We provide both the needed files and the script to pre-process the files after they are copied to the target path.

> System Prompts

System prompt is the core of the task. On agent end, it gives the agent better background information and guides it to better solve the on going task.

More important is the user part. Since our user is simulated by a LLM, then the system prompt of this user LLM serves as the core intent of this task. It should also give out all necessary information about this task, and define how the user LLM should interact with the agent (like tone, word preference, emotion etc) to pursue the diversity of real world users.

> Dumps

The complete interaction history between the agent and the user will be faithfully recorded under the `dumps` path, specifically, under the `task_root` in `TaskConfig`. The dumps both the local files as well as the dialogue history (including all queries, responses, tool calls, and tool returns).

> Evaluation

We use the recorded logs under `task_root` and the pre-defined groundtruth states `groundtruth/dev/filesystem_001` to check if the task is successfully solved. There are two main steps: 1) check the local states, and 2) check the dialogue history.

> Benchmark Global Config

To avoid entering model names, generation configurations and other parameters in each run. Now all these things are placed under a json file, see `scripts/eval_config.json`.
