WITH_SUDO=${1:-false}

# check if uv is here, if not, run "curl -LsSf https://astral.sh/uv/install.sh | sh" to install first
if ! command -v uv &> /dev/null; then
    echo "uv could not be found, please install via `curl -LsSf https://astral.sh/uv/install.sh | sh`"
    exit 1
fi

# Node.js and npm installation via NVM (only if not already installed)
echo "Checking Node.js and npm installation..."
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "Node.js or npm not found. Installing via NVM..."
    
    # Check if NVM is already installed
    if ! command -v nvm &> /dev/null; then
        echo "Installing NVM..."
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
        
        # Load NVM
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
        
        # Also add to current session
        source ~/.bashrc 2>/dev/null || true
    fi
    
    # Install Node.js v22.16.0 (includes npm)
    echo "Installing Node.js v22.16.0..."
    nvm install 22.16.0
    nvm use 22.16.0

    # Install npm v11.4.1
    echo "Installing npm v11.4.1..."
    npm install -g npm@11.4.1
    
    echo "Node.js and npm installed successfully!"
else
    echo "Node.js and npm are already installed."
    node -v
    npm -v
fi

# uv
uv sync

# k8s
echo "Tip: To support multiple k8s tasks, it is recommended to adjust inotify parameters. Please make sure you have sudo privileges."
echo "For temporary effect, run:"
echo "  sudo sysctl fs.inotify.max_user_watches=1048576"
echo "  sudo sysctl fs.inotify.max_user_instances=16384"
echo "  sudo sysctl fs.inotify.max_queued_events=16384"
echo "For permanent effect, append the following lines to /etc/sysctl.conf and then run 'sudo sysctl -p':"
echo "  fs.inotify.max_user_watches=1048576"
echo "  fs.inotify.max_user_instances=16384"
echo "  fs.inotify.max_queued_events=16384"
if [ "$WITH_SUDO" = true ]; then
    bash deployment/k8s/scripts/prepare.sh --sudo
    # configure inotify
    sudo sh -c 'echo "user.max_user_namespaces=10000" >> /etc/sysctl.conf'
    sudo sh -c 'echo "fs.inotify.max_user_watches=1048576" >> /etc/sysctl.conf'
    sudo sh -c 'echo "fs.inotify.max_user_instances=16384" >> /etc/sysctl.conf'
    sudo sh -c 'echo "fs.inotify.max_queued_events=16384" >> /etc/sysctl.conf'
    sudo sysctl -p
else
    bash deployment/k8s/scripts/prepare.sh --no-sudo
    # echo some so information to tell the user to configure inotify via sudo in some way
    echo "Please configure inotify via sudo to make sure you can run the k8s tasks in parallel."
    echo "For temporary effect, run:"
    echo "  sudo sysctl fs.inotify.max_user_watches=1048576"
    echo "  sudo sysctl fs.inotify.max_user_instances=16384"
    echo "  sudo sysctl fs.inotify.max_queued_events=16384"
    echo "  sudo sysctl user.max_user_namespaces=10000"
    echo "For permanent effect, append the following lines to /etc/sysctl.conf and then run 'sudo sysctl -p':"
    echo "  fs.inotify.max_user_watches=1048576"
    echo "  fs.inotify.max_user_instances=16384"
    echo "  fs.inotify.max_queued_events=16384"
    echo "  user.max_user_namespaces=10000"
fi

# install playwright
source .venv/bin/activate
export TMPDIR="./tmp" # make a folder for tmp files
mkdir -p $TMPDIR
playwright install chromium
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
uv tool install git+https://github.com/lockon-n/google-cloud-mcp@7df9ca22115002e0cea75deec595492c520df3e1
uv tool install emails-mcp@0.1.12
uv tool install git+https://github.com/lockon-n/mcp-snowflake-server@bca38f3ef5305ac53b9935bd09edbfac442b6a36
uv tool install git+https://github.com/lockon-n/mcp-scholarly@82a6ca268ae0d2e10664be396e1a0ea7aba23229

# local servers
rm -rf ./local_servers
mkdir -p local_servers

cd ./local_servers
git clone https://github.com/lockon-n/yahoo-finance-mcp
cd yahoo-finance-mcp
git checkout 469103ba1464486cb7b8bd2c1f6355f42ca64a5b
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
# check use podman or docker from configs/global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")
if [ "$podman_or_docker" = "podman" ]; then
    podman pull lockon0927/mcpbench-task-image-v2:jl0921alpha
else
    docker pull lockon0927/mcpbench-task-image-v2:jl0921alpha
fi