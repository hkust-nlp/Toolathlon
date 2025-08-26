## THIS FILE IS ONLY TBD STATUS
# # other preparation
mkdir -p ~/.gmail-mcp
mkdir -p ~/.calendar-mcp

cp ./configs/gcp-oauth.keys.json ~/.calendar-mcp/
cp ./configs/gcp-oauth.keys.json ~/.gmail-mcp/
cp ./configs/google_credentials.json  ~/.calendar-mcp/credentials.json
cp ./configs/google_credentials.json  ~/.gmail-mcp/credentials.json