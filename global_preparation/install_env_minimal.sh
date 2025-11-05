WITH_SUDO=${1:-false}

# cp two config files
echo "Copying config files..."
cp configs/global_configs_example.py configs/global_configs.py
cp configs/token_key_session_example.py configs/token_key_session.py

# check if uv is here, if not, run "curl -LsSf https://astral.sh/uv/install.sh | sh" to install first
if ! command -v uv &> /dev/null; then
    echo "uv could not be found, please install via 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
    exit 1
fi

# uv
uv sync

# k8s
echo "Tip: To support multiple k8s tasks, it is recommended to adjust inotify parameters. Please make sure you have sudo privileges."
if [ "$WITH_SUDO" = true ]; then
    bash deployment/k8s/scripts/prepare.sh --sudo
    # configure inotify
    echo "Configuring inotify directly via sudo..."
    sudo sh -c 'echo "user.max_user_namespaces=10000" >> /etc/sysctl.conf'
    sudo sh -c 'echo "fs.inotify.max_user_watches=1048576" >> /etc/sysctl.conf'
    sudo sh -c 'echo "fs.inotify.max_user_instances=16384" >> /etc/sysctl.conf'
    sudo sh -c 'echo "fs.inotify.max_queued_events=16384" >> /etc/sysctl.conf'
    sudo sysctl -p
else
    bash deployment/k8s/scripts/prepare.sh --no-sudo
    # echo some so information to tell the user to configure inotify via sudo in some way
    YELLOW='\033[1;33m'
    RESET='\033[0m'
    echo -e "${YELLOW}===============YOU SEE THIS CUZ YOU ARE NOT RUNNING AS ROOT/SUDO==============="
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
    echo "===============THIS WONT AFFECT THE QUICK START EXAMPLES, BUT JUST FULL EXECUTION==============="
    echo "===============SLEEP 5s FOR YOU TO READ THIS MESSAGE==============="
    echo -e "${RESET}"
fi