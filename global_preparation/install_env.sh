# check if uv is here, if not, run "curl -LsSf https://astral.sh/uv/install.sh | sh" to install first
if ! command -v uv &> /dev/null; then
    echo "uv could not be found, please install via `curl -LsSf https://astral.sh/uv/install.sh | sh`"
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
    
    # Install Node.js LTS version (includes npm)
    echo "Installing Node.js LTS..."
    nvm install --lts
    npm install -g npm@latest
    
    echo "Node.js and npm installed successfully!"
else
    echo "Node.js and npm are already installed."
    node -v
    npm -v
fi

# uv
uv sync

# npm
rm -rf node_modules
npm install
cd node_modules/@lockon0927/playwright-mcp-with-chunk
npx playwright install chromium
cd ../../..

# Set environment variable for Playwright (ignore host requirements warnings)
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
echo "export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1" >> ~/.bashrc

# uvx
uv tool install office-powerpoint-mcp-server@2.0.6
uv tool install office-word-mcp-server@1.1.9
uv tool install git+https://github.com/lockon-n/wandb-mcp-server@83f6d7fe2ad2e6b6278aef4a792f35dd765fd315
uv tool install git+https://github.com/lockon-n/cli-mcp-server@da1dcb5166597c9fbf90ede5fb1f0cd22a71a3b7
uv tool install pdf-tools-mcp@0.1.4
uv tool install git+https://github.com/jkawamoto/mcp-youtube-transcript@28081729905a48bef533d864efbd867a2bfd14cd
uv tool install mcp-google-sheets@0.4.1
uv tool install google-cloud-mcp@1.0.0
uv tool install emails-mcp@0.1.6
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
echo "\033[33mfixing npm audit issues...\033[0m"
npm audit fix

cd ../..

# Tesseract OCR installation (for users without sudo)
# echo "Setting up Tesseract OCR..."
# USERNAME="${USER}"
# BASE_DIR="/home/${USERNAME}"
# APPIMAGE_URL="https://github.com/AlexanderP/tesseract-appimage/releases/download/v5.5.1/tesseract-5.5.1-x86_64.AppImage"

# if [ ! -f "$BASE_DIR/local/bin/tesseract" ]; then
#     echo "Installing Tesseract 5.5.1..."
    
#     # Create directories
#     mkdir -p "$BASE_DIR/local/bin"
#     mkdir -p "$BASE_DIR/local/share/tessdata"
    
#     # Download AppImage
#     cd "$BASE_DIR/local/bin"
#     if [ ! -f "tesseract-5.5.1-x86_64.AppImage" ]; then
#         wget "$APPIMAGE_URL"
#         chmod +x tesseract-5.5.1-x86_64.AppImage
#     fi
    
#     # Create wrapper script
#     cat > tesseract << EOF
# #!/bin/bash
# exec "$BASE_DIR/local/bin/tesseract-5.5.1-x86_64.AppImage" "\$@"
# EOF
#     chmod +x tesseract
    
#     # Download language data
#     cd "$BASE_DIR/local/share/tessdata"
#     for lang in eng chi_sim; do
#         if [ ! -f "${lang}.traineddata" ]; then
#             echo "Downloading $lang language pack..."
#             wget "https://github.com/tesseract-ocr/tessdata/raw/main/${lang}.traineddata"
#         fi
#     done
    
#     # Add to PATH and set TESSDATA_PREFIX
#     echo "export PATH=\"$BASE_DIR/local/bin:\$PATH\"" >> ~/.bashrc
#     echo "export TESSDATA_PREFIX=\"$BASE_DIR/local/share/tessdata\"" >> ~/.bashrc
    
#     echo "Tesseract installed successfully!"
# else
#     echo "Tesseract already installed."
# fi
