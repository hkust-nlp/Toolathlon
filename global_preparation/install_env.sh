# check if uv is here, if not, run "curl -LsSf https://astral.sh/uv/install.sh | sh" to install first
if ! command -v uv &> /dev/null; then
    echo "uv could not be found, please install via `curl -LsSf https://astral.sh/uv/install.sh | sh`"
fi

# uv
uv sync

# install playwright
source .venv/bin/activate
export TMPDIR="./tmp" # make a folder for tmp files
mkdir -p $TMPDIR
playwright install-deps chromium
unset TMPDIR
rm -rf $TMPDIR

# npm
rm -rf node_modules
npm install
cd node_modules/@lockon0927/playwright-mcp-with-chunk
npx playwright install chromium
cd ../../..

# uvx
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

# local servers
rm -rf ./local_servers
mkdir -p local_servers

cd ./local_servers
git clone https://github.com/lockon-n/yahoo-finance-mcp
cd yahoo-finance-mcp
git checkout 27445a684dd2c65a6664620c5d057f66c42ea81f
uv sync
cd ../..

cd ./local_servers
git clone https://github.com/lockon-n/youtube-mcp-server
cd youtube-mcp-server
git checkout b202e00e9014bf74b9f5188b623cad16f13c01c4
npm install
npm run build
cd ../..

cd ./local_servers
git clone https://github.com/takashiishida/arxiv-latex-mcp.git
cd arxiv-latex-mcp
git checkout f8bd3b3b6d3d066fe29ba356023a0b3e8215da43
uv sync
cd ../..

cd local_servers
git clone https://github.com/matteoantoci/google-forms-mcp.git
cd google-forms-mcp
git checkout 96f7fa1ff02b8130105ddc6d98796f3b49c1c574
npm install
npm run build
printf "\033[33mfixing npm audit issues...\033[0m\n"
npm audit fix
cd ../..

# pull image
# check use podman  or docker from configs/global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")
if [ "$podman_or_docker" = "podman" ]; then
    podman pull lockon0927/mcpbench-task-image-v2:latest
else
    docker pull lockon0927/mcpbench-task-image-v2:latest
fi