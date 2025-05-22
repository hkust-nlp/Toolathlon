# MCPBench-Dev
----
#### NOTE: this readme is still under construction, please do not hesitiate to ping me (junlong) at any time. You are always welcomed!
----
### Quick Start

#### Basic Env Setup
0. install uv

    please refer to the official [website](https://github.com/astral-sh/uv), you may need to swithc on some proxies in this process

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

#### Demo

1. try `uv run demo.py`
