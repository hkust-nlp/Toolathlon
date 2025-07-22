In this file we guide you how to install all needed servers for this project.

1. install basic dependencies
    ```
    uv sync
    ```
    This will install all dependencies of this project, as well as some mcp servers built on third party python packages

    Therefore, instead of doing this once when you launch this project, please also **do this each time the servers are updated**.


2. install local npm packages
    ```
    npm install
    ```
    It will automatically check the `package.json` and `package-lock.json` (perferred) and installed the node.js packages recorded in it.

    If you encounter some proxy issue, see `FAQs/npx_install.md`.

    Similar to the python mcp servers, please **do this each time the servers are updated**.

3. install local uv tools

    Some mcp servers are launched via `uvx`, so we install them in advance to avoid installing them every time

    Note: They will be by default installed under ~/.local/share/uv/tool
    
    You can also assign another install dir via `UV_TOOL_DIR` envoronment var

    After you configurate these installation paths, please do the following

    ```
    uv tool install office-powerpoint-mcp-server
    uv tool install office-word-mcp-server
    uv tool install git+https://github.com/wandb/wandb-mcp-server
    uv tool install cli-mcp-server
    uv tool install pdf-tools-mcp@latest
    uv tool install git+https://github.com/jkawamoto/mcp-youtube-transcript
    ```

4. build from source

    There are also a small number of servers need to be built from source code, please check the following steps:

    `yahoo-finance-mcp`: see `install_records/yahoo_finance.md`

    `youtube-mcp-server`: see `install_records/youtube.md`

    `mcp-scholarly`: see `install_records/scholarly_search.md`

    `arxiv-latex`: see `install_records/arxiv_latex.md`

5. other preparation

    `playwright`: see `install_records/playwright.md`

    `gmail` & `google_calendar`: see `install_records/gmail_and_calendar.md`

    `ocr`: see `install_records/tesseract.md` (we need to install tesseract by ourselves on our lab cluster since no sudo is available)

5. configurate some tokens and keys
    
    Within the scope of this project, we have setup some keys and tokens by ourselves in `configs/token_key_session.py`, so you do not need to do it again by yourselves. Please just use them freely please.

    TODO: guide for community researchers who want to use our benchmark.

    TODOs: google cloud application, leetcode session, firecrawl token, edgeone token ...
    