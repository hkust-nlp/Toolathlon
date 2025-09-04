FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    software-properties-common \
    python3 \
    python3-pip \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install kind
RUN [ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 \
    && chmod +x ./kind \
    && mv ./kind /usr/local/bin/kind

# Set working directory
WORKDIR /workspace

# Copy package files for dependency installation
COPY package.json package-lock.json uv.lock pyproject.toml ./

# Install Python dependencies via uv
RUN uv sync --frozen

# Install Node.js dependencies
RUN npm ci

# Install playwright browsers in Python venv
RUN . .venv/bin/activate && playwright install chromium

# Install playwright in node_modules
RUN cd node_modules/@lockon0927/playwright-mcp-with-chunk && npx playwright install chromium

# Install uv tools
RUN uv tool install office-powerpoint-mcp-server@2.0.6 && \
    uv tool install office-word-mcp-server@1.1.9 && \
    uv tool install git+https://github.com/lockon-n/wandb-mcp-server@83f6d7fe2ad2e6b6278aef4a792f35dd765fd315 && \
    uv tool install git+https://github.com/lockon-n/cli-mcp-server@da1dcb5166597c9fbf90ede5fb1f0cd22a71a3b7 && \
    uv tool install pdf-tools-mcp@0.1.4 && \
    uv tool install git+https://github.com/jkawamoto/mcp-youtube-transcript@28081729905a48bef533d864efbd867a2bfd14cd && \
    uv tool install mcp-google-sheets@0.4.1 && \
    uv tool install google-cloud-mcp@1.0.0 && \
    uv tool install emails-mcp@0.1.12 && \
    uv tool install git+https://github.com/lockon-n/mcp-snowflake-server@75c03ca0b3cee2da831e2bc1b3b7a150e4c2999a && \
    uv tool install git+https://github.com/lockon-n/mcp-scholarly@82a6ca268ae0d2e10664be396e1a0ea7aba23229

# Create local_servers directory and install git-based servers
RUN mkdir -p local_servers

# Yahoo Finance MCP
RUN cd local_servers && \
    git clone https://github.com/lockon-n/yahoo-finance-mcp && \
    cd yahoo-finance-mcp && \
    git checkout 27445a684dd2c65a6664620c5d057f66c42ea81f && \
    uv sync

# YouTube MCP Server
RUN cd local_servers && \
    git clone https://github.com/lockon-n/youtube-mcp-server && \
    cd youtube-mcp-server && \
    git checkout b202e00e9014bf74b9f5188b623cad16f13c01c4 && \
    npm install && \
    npm run build

# Arxiv LaTeX MCP
RUN cd local_servers && \
    git clone https://github.com/takashiishida/arxiv-latex-mcp.git && \
    cd arxiv-latex-mcp && \
    git checkout f8bd3b3b6d3d066fe29ba356023a0b3e8215da43 && \
    uv sync

# Google Forms MCP
RUN cd local_servers && \
    git clone https://github.com/matteoantoci/google-forms-mcp.git && \
    cd google-forms-mcp && \
    git checkout 96f7fa1ff02b8130105ddc6d98796f3b49c1c574 && \
    npm install && \
    npm run build && \
    npm audit fix

# Create local_binary directory (will be populated by host mount)
RUN mkdir -p local_binary

# Verify installations
RUN uv --version && \
    node --version && \
    npm --version && \
    kubectl version --client && \
    kind version

CMD ["/bin/bash"]