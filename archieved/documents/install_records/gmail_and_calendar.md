this is the configuration guide for gmail and calendar servers

please do the following:
```
mkdir -p ~/.gmail-mcp
mkdir -p ~/.calendar-mcp

cp ./configs/gcp-oauth.keys.json ~/.calendar-mcp/
cp ./configs/gcp-oauth.keys.json ~/.gmail-mcp/
cp ./configs/credentials.json  ~/.calendar-mcp/
cp ./configs/credentials.json  ~/.gmail-mcp/
```

the `./configs/credentials.json` is generated via `uv run install_records/create_google_credentials.py`, it will use the `configs/gcp-oauth.keys.json` to generated this file.
