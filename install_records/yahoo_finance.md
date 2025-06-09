https://github.com/Alex2Yang97/yahoo-finance-mcp
请在 local_servers按照说明安装
* 不确定是否要fix commit id，暂时先不管，看起来功能很齐全
```
cd ./local_servers
git clone https://github.com/Alex2Yang97/yahoo-finance-mcp.git
cd yahoo-finance-mcp
uv venv
source .venv/bin/activate
uv pip install -e .
cd ..
```