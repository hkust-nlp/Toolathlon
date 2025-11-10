In this document we instruct how to register all needed accounts and how to fill in the token_key_session.py from these account info. Configuring all these accounts is a one-time effort, and will take around 30 minutes. 


### Part1 Overview
In part 1, we will introduce all accounts needed in launching full evaluation of Toolathlon.

#### Remote Ones
- google account x 1
    - to generate credentials
    - to generate api key
    - to generate service account
- github account x 1
    - to generate github tokens
- wandb account x 1
    - to generate wandb token
- notion account x 1
    - to generate connection secrets
- snowflake account x 1
    - to collect account, warehouse, etc
- huggingface account x 1
    - to generate Huggingface token

#### Local Ones
All local accounts will be already automatically created after you ran `bash global_preparation/deploy_containers.sh` following the main README.md.
see `configs/users_data.json` for all accounts we will create

We by default register all the accounts in `config/users_data.json` to Canvas and Poste, and we will register the #81 to #100 accounts to woocommerce and create a subsite for each of them.

### Part2 Register Remote Accounts and Configurate Them

#### Google Account
We recommand register a new Google (gmail) account for Toolathlon evaluation. You can use this google account for most of the services below such as wandb, notion, snowflake, etc.

First make sure you have `gcloud` sdk installed, e.g.:
```bash
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-456.0.0-linux-x86_64.tar.gz
tar -xf google-cloud-sdk-*-x86_64.tar.gz
./google-cloud-sdk/install.sh
source ~/.bashrc # or ~/.zshrc
```

Then go to [https://console.cloud.google.com/](https://console.cloud.google.com/) to accept the Terms of Service for this account before processing.

Finally, simply run:
```bash
bash global_preparation/automated_google_setup.sh
```
This script will help you setup new google cloud account, billing information, enable necessary APIs, etc. It will interact with you and sometimes will prompt you to some urls for manual authentication.

<details>
<summary>STEP 6 in this setup script requires some manual steps, click to expand for detailed figure instructions (these steps are already included in the script, the figures are just to help understand the process)</summary>

- Step 6.1 Configure OAuth Consent Screen  
![](./figures/gcp_oauth2_part2.2.png)

- Step 6.2 Publish the App  
![](./figures/gcp_oauth2_part5_1.png)

- Step 6.3 Create OAuth Client ID
Choose "Web application" as application type, give it a name and click "Create". For Web application, add http://localhost:3000/oauth2callback to the authorized redirect URIs
![](./figures/gcp_oauth2_part3.png)

- Download the JSON file of your client's OAuth keys  
![](./figures/gcp_oauth2_part4.png)
Rename this key json file to `gcp-oauth.keys.json` and place it under `configs`

</details>


#### Github & Huggingface & WandB & Serper Accounts
```bash
# This script will prompt you to do necessary registration and authentication.
bash global_preparation/automated_additional_services.sh
```

#### Notion Account
<!-- *This part is largely taken from [MCPMark](https://github.com/eval-sys/mcpmark/blob/main/docs/mcp/notion.md) -->

We recommand register a new notion account and create a new workspace.

First run `uv run -m global_preparation.special_setup_notion_official` to connect to the workspace in the above step to the official online notion mcp. This facilates us to duplicate and move pages more efficiently!

*Note: If you connect to an incorrect workspace when executing this command, you can remove the `~/.mcp-auth` and rerun this command to reset the login state of this online notion mcp.

<details>

<summary>If you indeed want to do notion preprocessing via playwright ... (NOT RECOMMANDED!)</summary>

First run `uv run utils/app_specific/notion/notion_login_helper.py --headless` to generate a `notion_state.json` under the `configs`, please just follow the instructions from the script, this is a one-time effort.

You also need to change the variable `notion_preprocess_with_playwright` to `True` in `configs/global_configs.py`

</details>
--


Please duplicate the public page [Notion Source Page](https://amazing-wave-b38.notion.site/Notion-Source-Page-27ad10a48436805b9179fdaff2f65be2) to your workspace,
record the url of this duplicated page (not our public page) as the `source_notion_page_url` variable in `configs/token_key_session.py`

Please also create a new page called `Notion Eval Page` directly under your workspace,
record the url if this new page as the `eval_notion_page_url` variable in `configs/token_key_session.py`

Also, create an intrgration that include these above two pages, see https://www.notion.so/profile/integrations, and record the "Internal Integration Secret" as `notion_integration_key` veriable in `configs/token_key_session.py`
![](./figures/notion_part1.png)
![](./figures/notion_part2.png)
![](./figures/notion_part3.png)

Finally, similar to the above steps, create an intrgration key for evaluation use only. Please only select `Notion Eval Page` into the access range of it. Record this key as `notion_integration_key_eval` variable in `configs/token_key_session.py`.


#### SnowFlake Account
We recommand register a new Snowflake account (see https://signup.snowflake.com/). After you have created and activated the account. Find your account details and fill them into the `snowflake_account`, `snowflake_role`, `snowflake_user` and `snowflake_password` variables in `configs/token_key_session.py`
![](./figures/snowflake_part1.png)
![](./figures/snowflake_part2.png)
