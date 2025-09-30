# record start time
start_time=$(date +%s)
echo "Start time: $(date)"

poste_configure_dovecot=${1:-true}
create_test_k8s_cluster=${2:-true}

bash deployment/k8s/scripts/prepare.sh --no-sudo # or no-sudo if you cannot use sudo, this will install some needed commands
# this is just a test cluster to make sure the MCP servers are ready to use
bash deployment/k8s/scripts/setup.sh # this is to create a test cluster

bash deployment/canvas/scripts/setup.sh # port 10001 20001

bash deployment/poste/scripts/setup.sh $poste_configure_dovecot # port 10005 2525 1143 2587

bash deployment/woocommerce/scripts/setup.sh start 81 20 # port 10003

# we also use 30123, 30124 ports in two of the k8s tasks

# record exit time
echo "Exit time: $(date)"

# record total time
echo "Total time: $(($(date +%s) - start_time)) seconds"