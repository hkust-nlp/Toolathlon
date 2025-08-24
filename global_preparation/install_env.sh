# uv
uv sync

# npm
rm -rf node_modules
npm install
cd node_modules/@lockon0927/playwright-mcp-with-chunk
npx playwright install chromium
cd ../../..

# uvx
uv tool install office-powerpoint-mcp-server@2.0.6
uv tool install office-word-mcp-server@1.1.9
uv tool install git+https://github.com/wandb/wandb-mcp-server@e1b6274a58a8dc56a47c5aaefb9d03282133f507
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