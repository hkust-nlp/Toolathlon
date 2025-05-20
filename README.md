# MCPBench-Dev
----
#### NOTE: this readme is still under construction, please do not hesitiate to ping me (junlong) at any time. You are always welcomed!
----
#### Quick Start
0. you may need to set some proxy for your PC/Dev machine. Also, please fill in `configs/global_configs.py`

1. set up env
    ```
    conda create -n mcpbench_dev python=3.12
    pip install -r requirements.txt
    ```

2. install npm (see `FAQs/npm_install.md`)

3. install local npm packages
    ```
    npm install
    ```
    it will automatically check the `package.json` and `package-lock.json`
    you may encounter some proxy issue, see `FAQs/npx_install.md`.

4. try `python demo.py`
