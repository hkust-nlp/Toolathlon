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

# config some parameters for multiple k8s
# you should have sudo to do so
sudo sysctl fs.inotify.max_user_watches=1048576
sudo sysctl fs.inotify.max_user_instances=16384
sudo sysctl fs.inotify.max_queued_events=16384