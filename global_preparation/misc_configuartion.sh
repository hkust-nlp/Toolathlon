## THIS FILE IS ONLY TBD STATUS
# # other preparation

# if no configs/global_configs.py, just copy configs/global_configs_example.py to configs/global_configs.py
if [ ! -f configs/global_configs.py ]; then
    cp configs/global_configs_example.py configs/global_configs.py
fi

mkdir -p ~/.gmail-mcp
mkdir -p ~/.calendar-mcp

cp ./configs/gcp-oauth.keys.json ~/.calendar-mcp/
cp ./configs/gcp-oauth.keys.json ~/.gmail-mcp/
cp ./configs/google_credentials.json  ~/.calendar-mcp/credentials.json
cp ./configs/google_credentials.json  ~/.gmail-mcp/credentials.json