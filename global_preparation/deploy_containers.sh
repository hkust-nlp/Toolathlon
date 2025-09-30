# record start time
start_time=$(date +%s)
echo "Start time: $(date)"

poste_configure_dovecot=${1:-true}
echo "============================================================================================="
echo "poste_configure_dovecot: $poste_configure_dovecot"
echo "For some Linux distributions, you need to configure Dovecot to allow plaintext auth."
echo "If you are not sure, please set to true."
echo "Our experience: Ubuntu 24.04 should set this as true, but AlmaLinux should set this as false."
echo "============================================================================================="

sleep 5

# this is just to launch a test cluster (also clear existing ones) to make sure the MCP servers are ready to use
bash deployment/k8s/scripts/setup.sh # this is to create one test cluster

bash deployment/canvas/scripts/setup.sh # port 10001 20001

bash deployment/poste/scripts/setup.sh start $poste_configure_dovecot # port 10005 2525 1143 2587

bash deployment/woocommerce/scripts/setup.sh start 81 20 # port 10003

# we also use 30123, 30124 ports in two of the k8s tasks

# record exit time
echo "Exit time: $(date)"

# record total time
echo "Total time: $(($(date +%s) - start_time)) seconds"