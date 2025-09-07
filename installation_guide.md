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

    Note: They will be by default installed under ~/.local/share/uv/tools
    
    You can also assign another install dir via `UV_TOOL_DIR` envoronment var

    After you configurate these installation paths, please do the following

    ```
    uv tool install office-powerpoint-mcp-server@2.0.6
    uv tool install office-word-mcp-server@1.1.9
    uv tool install git+https://github.com/lockon-n/wandb-mcp-server@83f6d7fe2ad2e6b6278aef4a792f35dd765fd315
    uv tool install git+https://github.com/lockon-n/cli-mcp-server@da1dcb5166597c9fbf90ede5fb1f0cd22a71a3b7
    uv tool install pdf-tools-mcp@0.1.4
    uv tool install git+https://github.com/jkawamoto/mcp-youtube-transcript@28081729905a48bef533d864efbd867a2bfd14cd
    uv tool install mcp-google-sheets@0.4.1
    uv tool install google-cloud-mcp@1.0.0
    uv tool install emails-mcp@0.1.12
    uv tool install git+https://github.com/lockon-n/mcp-snowflake-server@75c03ca0b3cee2da831e2bc1b3b7a150e4c2999a
    uv tool install git+https://github.com/lockon-n/mcp-scholarly@82a6ca268ae0d2e10664be396e1a0ea7aba23229
    ```

4. build from source

    There are also a small number of servers need to be built from source code, please check the following steps:

    `yahoo-finance-mcp`: see `install_records/yahoo_finance.md`

    `youtube-mcp-server`: see `install_records/youtube.md`

    `arxiv-latex`: see `install_records/arxiv_latex.md`

    `google-forms`: see `install_records/google_forms.md`

5. other preparation

    `playwright`: see `install_records/playwright.md`

    `gmail` & `google_calendar`: see `install_records/gmail_and_calendar.md`

    `ocr`: see `install_records/tesseract.md` (we need to install tesseract by ourselves on our lab cluster since no sudo is available)

4.5 prepare accounts

    please register some accounts, see accounts.md, and prepare credentials, tokens, sessions etc (TO BE FINISHED)

5. configurate some tokens and keys
    
    Within the scope of this project, we have setup some keys and tokens by ourselves in `configs/token_key_session.py`, so you do not need to do it again by yourselves. Please just use them freely please.

6. other preparation

    (TO BE FINISHED)