#!/bin/bash

# Usage instructions
usage() {
    echo "Usage: $0 [--sudo|--no-sudo]"
    echo "  --sudo      : Install with sudo (default)"
    echo "  --no-sudo   : Install to user local bin directory (~/bin) without sudo"
    exit 1
}

# Default: use sudo
USE_SUDO=1

# Parse arguments
if [ "$1" == "--no-sudo" ]; then
    USE_SUDO=0
elif [ "$1" == "--sudo" ] || [ -z "$1" ]; then
    USE_SUDO=1
elif [ -n "$1" ]; then
    usage
fi

if [ $USE_SUDO -eq 1 ]; then
    INSTALL_KIND_PATH="/usr/local/bin/kind"
    INSTALL_KUBECTL_PATH="/usr/local/bin/kubectl"
    SUDO="sudo"
else
    mkdir -p ~/bin
    INSTALL_KIND_PATH="$HOME/bin/kind"
    INSTALL_KUBECTL_PATH="$HOME/bin/kubectl"
    SUDO=""
    # Ensure user's bin directory is in PATH
    if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
        echo "Please add \$HOME/bin to your PATH, for example add the following to your ~/.bashrc or ~/.zshrc:"
        echo 'export PATH="$HOME/bin:$PATH"'
    fi
fi

# Install kind
if command -v kind &> /dev/null; then
    echo "kind is already installed at: $(which kind)"
else
    echo "Installing kind..."
    curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
    chmod +x ./kind
    $SUDO mv ./kind "$INSTALL_KIND_PATH"
    echo "kind has been installed to: $INSTALL_KIND_PATH"
fi

# Install kubectl
if command -v kubectl &> /dev/null; then
    echo "kubectl is already installed at: $(which kubectl)"
else
    echo "Installing kubectl..."
    KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
    chmod +x kubectl
    $SUDO mv kubectl "$INSTALL_KUBECTL_PATH"
    echo "kubectl has been installed to: $INSTALL_KUBECTL_PATH"
fi