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

see `scripts/debug_manual.sh` for more details

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

If you want to 

> Evaluation

We use the recorded logs under `task_root` and the pre-defined groundtruth states `groundtruth/dev/filesystem_001` to check if the task is successfully solved. There are two main steps: 1) check the local states, and 2) check the dialogue history.

> Benchmark Global Config

To avoid entering model names, generation configurations and other parameters in each run. Now all these things are placed under a json file, see `scripts/eval_config.json`.