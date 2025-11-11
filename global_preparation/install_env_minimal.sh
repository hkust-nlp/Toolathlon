WITH_SUDO=${1:-false}

# cp two config files
if [ ! -f configs/global_configs.py ]; then
    echo "Copying configs/global_configs_example.py to configs/global_configs.py..."
    cp configs/global_configs_example.py configs/global_configs.py
else
    echo "configs/global_configs.py already exists, skipping copy."
fi

if [ ! -f configs/token_key_session.py ]; then
    echo "Copying configs/token_key_session_example.py to configs/token_key_session.py..."
    cp configs/token_key_session_example.py configs/token_key_session.py
else
    echo "configs/token_key_session.py already exists, skipping copy."
fi

# check if uv is here, if not, run "curl -LsSf https://astral.sh/uv/install.sh | sh" to install first
if ! command -v uv &> /dev/null; then
    echo "uv could not be found, please install via 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
    exit 1
fi

# uv
uv sync

# Try to load NVM first if it exists
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    \. "$NVM_DIR/nvm.sh"
    # Try to use the target version if already installed
    nvm use 22.16.0 2>/dev/null || true
fi

NEED_INSTALL=false

# Check if Node.js and npm are installed
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "Node.js or npm not found. Will install..."
    NEED_INSTALL=true
else
    # Check Node.js version (require >= 22)
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -lt 22 ]; then
        echo "Node.js version $(node -v) is too old (require >= 22). Will install v22.16.0..."
        NEED_INSTALL=true
    fi

    # Check npm version (require >= 11)
    NPM_VERSION=$(npm -v | cut -d. -f1)
    if [ "$NPM_VERSION" -lt 11 ]; then
        echo "npm version $(npm -v) is too old (require >= 11). Will install v11.4.1..."
        NEED_INSTALL=true
    fi

    if [ "$NEED_INSTALL" = false ]; then
        echo "Node.js $(node -v) and npm $(npm -v) meet requirements."
    fi
fi

# Install if needed
if [ "$NEED_INSTALL" = true ]; then
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
    else
        # Load NVM if already installed
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi

    # Install Node.js v22.16.0 (includes npm)
    echo "Installing Node.js v22.16.0..."
    nvm install 22.16.0
    nvm use 22.16.0

    # Set as default version for all new shells
    echo "Setting Node.js v22.16.0 as default..."
    nvm alias default 22.16.0

    # Install npm v11.4.1
    echo "Installing npm v11.4.1..."
    npm install -g npm@11.4.1

    echo "Node.js and npm installed successfully!"
    echo "Installed versions: Node.js $(node -v), npm $(npm -v)"
fi

npm install

# k8s
echo "Tip: To support multiple k8s tasks, it is recommended to adjust inotify parameters. Please make sure you have sudo privileges."
if [ "$WITH_SUDO" = true ]; then
    bash deployment/k8s/scripts/prepare.sh --sudo
    echo "Configuring inotify directly via sudo..."
    SYSCTL_CONF="/etc/sysctl.conf"
    declare -A inotify_settings=(
        ["user.max_user_namespaces"]="10000"
        ["fs.inotify.max_user_watches"]="1048576"
        ["fs.inotify.max_user_instances"]="16384"
        ["fs.inotify.max_queued_events"]="16384"
    )
    for key in "${!inotify_settings[@]}"; do
        value="${inotify_settings[$key]}"
        # Check if the setting already exists and has the correct value
        if grep -q "^$key\s*=" "$SYSCTL_CONF"; then
            # If exists, but value is different, replace it
            sudo sed -i "s|^$key\s*=.*|$key=$value|" "$SYSCTL_CONF"
        else
            # If not found, append to file
            echo "$key=$value" | sudo tee -a "$SYSCTL_CONF" > /dev/null
        fi
    done
    sudo sysctl -p
else
    bash deployment/k8s/scripts/prepare.sh --no-sudo
    YELLOW='\033[1;33m'
    RESET='\033[0m'
    echo -e "${YELLOW}===============YOU SEE THIS CUZ YOU ARE NOT RUNNING AS ROOT/SUDO==============="
    echo "Please configure inotify via sudo to make sure you can run the k8s tasks in parallel."
    echo "For temporary effect, run:"
    echo "  sudo sysctl fs.inotify.max_user_watches=1048576"
    echo "  sudo sysctl fs.inotify.max_user_instances=16384"
    echo "  sudo sysctl fs.inotify.max_queued_events=16384"
    echo "  sudo sysctl user.max_user_namespaces=10000"
    echo "For permanent effect, please make sure you only append the following lines to /etc/sysctl.conf if they do not already exist, then run 'sudo sysctl -p':"
    echo "  fs.inotify.max_user_watches=1048576"
    echo "  fs.inotify.max_user_instances=16384"
    echo "  fs.inotify.max_queued_events=16384"
    echo "  user.max_user_namespaces=10000"
    echo "Tip: You can use 'grep' to check if a setting already exists in /etc/sysctl.conf, for example: grep fs.inotify.max_user_watches /etc/sysctl.conf"
    echo "===============THIS WONT AFFECT THE QUICK START EXAMPLES, BUT JUST FULL EXECUTION==============="
    echo "===============SLEEP 5s FOR YOU TO READ THIS MESSAGE==============="
    echo -e "${RESET}"
fi